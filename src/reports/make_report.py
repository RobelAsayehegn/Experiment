"""Build reports/REPORT.md from validation_results.json (+ lockbox_results.json if present).

Usage:  python -m src.reports.make_report
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "reports"
PCT = lambda x: "n/a" if x is None or pd.isna(x) else f"{x:+.1%}"  # noqa: E731
PCT2 = lambda x: "n/a" if x is None or pd.isna(x) else f"{x:+.2%}"  # noqa: E731


def table(rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    head = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def perf_rows(results: dict, bh_key=None) -> list[dict]:
    rows = []
    for key, r in results.items():
        strat, coin = key.split("|")
        m = r["metrics"]
        bh = r["buy_hold"]["net_return"] if "buy_hold" in r else bh_key[coin]
        rows.append({
            "strategy": strat, "coin": coin.replace("USDT", ""),
            "net return": PCT(m["net_return"]), "buy&hold": PCT(bh),
            "random (mean)": PCT(r["random"]["mean_return"]), "beats random %": f"{r['percentile_vs_random']:.0f}",
            "trades": m["n_trades"], "win rate": "n/a" if pd.isna(m["win_rate"]) else f"{m['win_rate']:.0%}",
            "expectancy/trade": PCT2(m["expectancy_per_trade"]), "profit factor": f"{m['profit_factor']:.2f}",
            "Sharpe": f"{m['sharpe']:.2f}", "max DD": PCT(m["max_drawdown"]), "fees paid $": f"{m['fees_paid']:.0f}",
        })
    return rows


def summary_by_strategy(results: dict, bh: dict | None) -> list[dict]:
    rows = {}
    for key, r in results.items():
        strat, coin = key.split("|")
        m = r["metrics"]
        b = r["buy_hold"]["net_return"] if "buy_hold" in r else bh[coin]
        d = rows.setdefault(strat, {"ret": [], "bh": [], "exp": [], "n": 0, "pct": [], "pos": 0})
        d["ret"].append(m["net_return"]); d["bh"].append(b); d["exp"].append(m["expectancy_per_trade"])
        d["n"] += m["n_trades"]; d["pct"].append(r["percentile_vs_random"]); d["pos"] += m["net_return"] > 0
    out = []
    for s, d in rows.items():
        n = len(d["ret"])
        out.append({"strategy": s, "avg net return (3 coins)": PCT(sum(d["ret"]) / n), "avg buy&hold": PCT(sum(d["bh"]) / n),
                    "coins profitable": f"{d['pos']}/{n}", "avg expectancy/trade": PCT2(pd.Series(d["exp"]).mean()),
                    "total trades": d["n"], "avg beats-random %": f"{sum(d['pct']) / n:.0f}"})
    return out


def edge_verdict(results: dict) -> tuple[int, int]:
    """Count strategy x coin cells with positive expectancy and >=95th percentile vs random."""
    good = sum(1 for r in results.values()
               if r["metrics"]["expectancy_per_trade"] > 0 and r["metrics"]["net_return"] > 0 and r["percentile_vs_random"] >= 95)
    return good, len(results)


def main() -> None:
    v = json.loads((OUT / "validation_results.json").read_text())
    lock_path = OUT / "lockbox_results.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else None
    meta = v["meta"]
    bh_wf = {c: x["walk_forward"]["net_return"] for c, x in v["buy_hold"].items()}
    L = ["# Crypto Research Lab: Phase 1 report", ""]
    L += ["## Setup", "",
          f"- Data: Binance spot, public archive, {', '.join(c.replace('USDT', '') for c in meta['coins'])}, {meta['interval']} candles, 2023-10-01 to 2026-08-31. Checksums verified, no gaps/duplicates.",
          f"- Costs on every trade: fee {meta['fee']:.2%} + slippage {meta['slippage']:.2%} per side (round trip {2 * (meta['fee'] + meta['slippage']):.2%}). Long-only, fully invested when in a trade, signal on bar t executes at bar t+1 open.",
          f"- Periods: **train** {meta['train'][0][:10]} to {meta['train'][1][:10]}; **walk-forward** {meta['walk_forward'][0][:10]} to {meta['walk_forward'][1][:10]} "
          "(3-month folds, parameters re-chosen on all earlier data before each fold, chosen by net Sharpe); **lockbox** last 6 months, evaluated once.",
          f"- Parameter combinations tried: **{meta['combinations_per_coin']} per coin** ({meta['combinations_per_coin'] * len(meta['coins'])} strategy/coin configurations) "
          "across 5 strategies. Small grids on purpose; with this many tries a few 'good looking' results are expected by luck alone.",
          "- 'Beats random %' = share of 200 random-entry runs (same trade count and average holding time, same costs) that the strategy out-earned. ~50 is luck, >=95 is notable.", ""]

    L += ["## 1. Walk-forward validation (unseen data, parameters re-picked each fold)", "",
          "### By strategy (average over BTC/ETH/SOL)", "", table(summary_by_strategy(v["walk_forward"], bh_wf)),
          "### Every strategy x coin", "", table(perf_rows(v["walk_forward"], bh_wf)), ""]

    L += ["## 2. Overfitting check: in-sample vs. out-of-sample", "",
          "Train window = what an optimiser would report. Walk-forward = what actually happened afterwards.", ""]
    rows = []
    for key, r in v["train_in_sample"].items():
        wf = v["walk_forward"][key]["metrics"]
        s, c = key.split("|")
        rows.append({"strategy": s, "coin": c.replace("USDT", ""), "best params (train)": json.dumps(r["params"]),
                     "train net return": PCT(r["metrics"]["net_return"]), "train expectancy": PCT2(r["metrics"]["expectancy_per_trade"]),
                     "walk-forward expectancy": PCT2(wf["expectancy_per_trade"])})
    L += [table(rows), ""]

    L += ["## 3. Stability across time (all parameter sets in the grid)", "",
          "Median net return of the *whole grid* per period, and share of grid configs that were profitable. Strategies that only work in one regime show up here.", ""]
    rows = []
    for key, sw in v["grid_sweep"].items():
        s, c = key.split("|")
        row = {"strategy": s, "coin": c.replace("USDT", "")}
        for label, d in sw.items():
            row[label] = f"{PCT(d['median'])} ({d['share_positive']:.0%} pos) vs B&H {PCT(d['buy_hold'])}"
        rows.append(row)
    L += [table(rows), ""]

    L += ["## 4. Lockbox (last 6 months, evaluated once)", ""]
    if lock:
        L += [f"Period {lock['period_start'][:10]} to {lock['period_end'][:10]}. Parameters frozen from all pre-lockbox data.", "",
              "### By strategy", "", table(summary_by_strategy(lock["results"], None)),
              "### Every strategy x coin", "", table(perf_rows(lock["results"])), ""]
    else:
        L += ["_Not yet evaluated._", ""]

    gw, nw = edge_verdict(v["walk_forward"])
    L += ["## 5. Verdict", "",
          f"Evidence-of-edge test per strategy/coin cell: positive net return, positive expectancy per trade, and beating >=95% of random-entry runs.",
          f"- Walk-forward: **{gw} of {nw}** cells pass."]
    if lock:
        gl, nl = edge_verdict(lock["results"])
        L += [f"- Lockbox: **{gl} of {nl}** cells pass."]
    L += ["", "_(Hand-written interpretation is appended below by the researcher.)_", ""]
    (OUT / "REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote reports/REPORT.md")


if __name__ == "__main__":
    main()

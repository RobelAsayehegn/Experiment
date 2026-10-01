"""Train + walk-forward validation for one timeframe (the lockbox is NOT touched here).

Covers every long-only and long/short strategy variant on every coin; one process per coin.

Usage:  python -m src.reports.run_validation --interval 1h|4h   -> reports/results/validation_<interval>.json
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from src.backtest import validation as V
from src.backtest.engine import DEFAULT_FEE, DEFAULT_SHORT_COST_PER_HOUR, DEFAULT_SLIPPAGE
from src.backtest.metrics import compute_metrics
from src.data.download import SYMBOLS
from src.data.quality import load
from src.strategies.baselines import buy_and_hold
from src.strategies.registry import STRATEGIES

OUT = Path(__file__).resolve().parents[2] / "reports" / "results"
SWEEP_PERIODS = {
    "2023-10..2024-09": (V.TRAIN_START, V.TRAIN_END),
    "2024-10..2025-09": (V.TS("2024-10-01"), V.TS("2025-10-01")),
    "2025-10..2026-02": (V.TS("2025-10-01"), V.WF_END),
}
CURVE_POINTS = 300


def curve(equity, bh_equity) -> dict:
    """Downsample an equity curve and its buy&hold twin to ~CURVE_POINTS points (normalised to 1.0)."""
    step = max(1, len(equity) // CURVE_POINTS)
    idx = list(range(0, len(equity), step)) + ([len(equity) - 1] if (len(equity) - 1) % step else [])
    return {"t": [str(equity.index[i])[:10] for i in idx],
            "strategy": [round(float(equity.iloc[i] / equity.iloc[0]), 4) for i in idx],
            "buy_hold": [round(float(bh_equity.iloc[i] / bh_equity.iloc[0]), 4) for i in idx]}


def process_coin(sym: str, interval: str) -> dict:
    t0 = time.time()
    asset = V.Asset(sym, load(sym, interval), {}, interval)
    wf_start, wf_end = V.TRAIN_END, V.WF_END
    bh_res = asset.run(buy_and_hold(asset.df), wf_start, wf_end)
    out = {"buy_hold": {"walk_forward": compute_metrics(bh_res),
                        "train": compute_metrics(asset.run(buy_and_hold(asset.df), V.TRAIN_START, V.TRAIN_END))},
           "variants": {}}
    for strat, (_, grid) in STRATEGIES.items():
        two_sided = strat.endswith("_ls")
        p0, m0 = V.select_params(asset, strat, V.TRAIN_START, V.TRAIN_END)
        fold_res, chosen, fold_returns = [], [], []
        for a, b in zip(V.FOLD_EDGES[:-1], V.FOLD_EDGES[1:]):
            p, _ = V.select_params(asset, strat, V.TRAIN_START, a)
            r = V.run_backtest_slice(asset, strat, p, a, b)
            fold_res.append(r)
            chosen.append({"fold_start": str(a)[:10], "params": p})
            fold_returns.append(float(r.equity.iloc[-1] / r.initial_capital - 1))
        res = V.chain(fold_res)
        met = compute_metrics(res)
        rnd = V.random_baseline(asset, wf_start, wf_end, met["n_trades"], V.avg_hold_bars(res), two_sided=two_sided)
        pct = float((np.array(rnd.pop("returns")) < met["net_return"]).mean() * 100)

        sweep = {}
        for label, (a, b) in SWEEP_PERIODS.items():
            rets = [compute_metrics(asset.run(asset.weights(strat, p), a, b))["net_return"] for p in grid]
            bh = compute_metrics(asset.run(buy_and_hold(asset.df), a, b))["net_return"]
            sweep[label] = {"median": float(np.median(rets)), "best": float(max(rets)), "worst": float(min(rets)),
                            "share_positive": float(np.mean(np.array(rets) > 0)), "buy_hold": bh}
        out["variants"][strat] = {
            "train_in_sample": {"params": p0, "metrics": m0},
            "walk_forward": {"metrics": met, "chosen_params": chosen, "fold_returns": fold_returns,
                             "random": rnd, "percentile_vs_random": pct,
                             "curve": curve(res.equity, bh_res.equity)},
            "grid_sweep": sweep,
        }
        print(f"[{interval}] {strat:26s} {sym}  WF net {met['net_return']:+7.1%}  trades {met['n_trades']:4d}  "
              f"exp {met['expectancy_per_trade']:+.3%}  rnd-pct {pct:3.0f}  ({time.time() - t0:.0f}s)", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", choices=["1h", "4h"], required=True)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    n_variants = len(STRATEGIES)
    meta = {"fee": DEFAULT_FEE, "slippage": DEFAULT_SLIPPAGE, "short_cost_per_8h": DEFAULT_SHORT_COST_PER_HOUR * 8,
            "combinations_per_coin": V.n_combinations(), "variants": n_variants, "coins": SYMBOLS,
            "interval": args.interval, "selection_metric": "net Sharpe (>=5 trades)",
            "train": [str(V.TRAIN_START), str(V.TRAIN_END)], "walk_forward": [str(V.TRAIN_END), str(V.WF_END)],
            "folds": [str(e) for e in V.FOLD_EDGES]}
    with ProcessPoolExecutor(max_workers=len(SYMBOLS)) as ex:
        futs = {s: ex.submit(process_coin, s, args.interval) for s in SYMBOLS}
        coins = {s: f.result() for s, f in futs.items()}
    (OUT / f"validation_{args.interval}.json").write_text(json.dumps({"meta": meta, "coins": coins}, default=float), encoding="utf-8")
    print(f"saved reports/results/validation_{args.interval}.json")


if __name__ == "__main__":
    main()

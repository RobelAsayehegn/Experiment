"""Train + walk-forward validation (the lockbox is NOT touched here).

Usage:  python -m src.reports.run_validation   -> reports/validation_results.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from src.backtest import validation as V
from src.backtest.engine import DEFAULT_FEE, DEFAULT_SLIPPAGE
from src.backtest.metrics import compute_metrics
from src.data.download import SYMBOLS
from src.data.quality import load
from src.strategies.baselines import buy_and_hold
from src.strategies.registry import STRATEGIES

OUT = Path(__file__).resolve().parents[2] / "reports"
SWEEP_PERIODS = {
    "2023-10..2024-09": (V.TRAIN_START, V.TRAIN_END),
    "2024-10..2025-09": (V.TS("2024-10-01"), V.TS("2025-10-01")),
    "2025-10..2026-02": (V.TS("2025-10-01"), V.WF_END),
}


def main() -> None:
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    out = {"meta": {"fee": DEFAULT_FEE, "slippage": DEFAULT_SLIPPAGE, "combinations_per_coin": V.n_combinations(),
                    "coins": SYMBOLS, "interval": "1h", "selection_metric": "net Sharpe (>=5 trades)",
                    "train": [str(V.TRAIN_START), str(V.TRAIN_END)], "walk_forward": [str(V.TRAIN_END), str(V.WF_END)],
                    "folds": [str(e) for e in V.FOLD_EDGES]},
           "train_in_sample": {}, "walk_forward": {}, "grid_sweep": {}, "buy_hold": {}}
    wf_start, wf_end = V.TRAIN_END, V.WF_END

    for sym in SYMBOLS:
        asset = V.Asset(sym, load(sym, "1h"), {})
        out["buy_hold"][sym] = {
            "walk_forward": compute_metrics(asset.run(buy_and_hold(asset.df), wf_start, wf_end)),
            "train": compute_metrics(asset.run(buy_and_hold(asset.df), V.TRAIN_START, V.TRAIN_END)),
        }
        for strat, (_, grid) in STRATEGIES.items():
            key = f"{strat}|{sym}"
            # --- training period: what an optimiser would brag about (in-sample) ---
            p0, m0 = V.select_params(asset, strat, V.TRAIN_START, V.TRAIN_END)
            out["train_in_sample"][key] = {"params": p0, "metrics": m0}

            # --- walk-forward: re-select on all earlier data, trade the next fold ---
            fold_res, chosen = [], []
            for a, b in zip(V.FOLD_EDGES[:-1], V.FOLD_EDGES[1:]):
                p, _ = V.select_params(asset, strat, V.TRAIN_START, a)
                chosen.append({"fold_start": str(a)[:10], "params": p})
                fold_res.append(V.run_backtest_slice(asset, strat, p, a, b))
            res = V.chain(fold_res)
            met = compute_metrics(res)
            rnd = V.random_baseline(asset, wf_start, wf_end, met["n_trades"], V.avg_hold_bars(res))
            pct = float((np.array(rnd.pop("returns")) < met["net_return"]).mean() * 100)
            out["walk_forward"][key] = {"metrics": met, "chosen_params": chosen,
                                         "random": rnd, "percentile_vs_random": pct}

            # --- grid sweep by period: do configs work across time, or only in one regime? ---
            sweep = {}
            for label, (a, b) in SWEEP_PERIODS.items():
                rets = [compute_metrics(asset.run(asset.weights(strat, p), a, b))["net_return"] for p in grid]
                bh = compute_metrics(asset.run(buy_and_hold(asset.df), a, b))["net_return"]
                sweep[label] = {"median": float(np.median(rets)), "best": float(max(rets)), "worst": float(min(rets)),
                                "share_positive": float(np.mean(np.array(rets) > 0)), "buy_hold": bh}
            out["grid_sweep"][key] = sweep
            print(f"{key:36s} WF net {met['net_return']:+7.1%}  trades {met['n_trades']:4d}  "
                  f"expectancy {met['expectancy_per_trade']:+.3%}  vs random pct {pct:.0f}  ({time.time() - t0:.0f}s)")

    (OUT / "validation_results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("saved reports/validation_results.json")


if __name__ == "__main__":
    main()

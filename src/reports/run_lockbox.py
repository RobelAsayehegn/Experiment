"""Evaluate the LOCKBOX period (last 6 months) exactly once.

Parameters are chosen on all pre-lockbox data (train + walk-forward period) and then frozen.
The result file doubles as the "already used" marker: if it exists, this script refuses to run.
Nothing may be tuned after looking at these numbers (CLAUDE.md).

Usage:  python -m src.reports.run_lockbox
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.backtest import validation as V
from src.data.download import SYMBOLS
from src.data.quality import load
from src.strategies.registry import STRATEGIES

OUT = Path(__file__).resolve().parents[2] / "reports"
RESULT = OUT / "lockbox_results.json"


def main() -> None:
    if RESULT.exists():
        raise SystemExit(f"Lockbox already evaluated ({RESULT.name} exists). It is a one-shot test; refusing to re-run.")
    if not (OUT / "validation_results.json").exists():
        raise SystemExit("Run run_validation first: the lockbox is the last step.")

    out = {"period_start": str(V.LOCKBOX_START), "results": {}}
    for sym in SYMBOLS:
        asset = V.Asset(sym, load(sym, "1h"), {})
        end = asset.df["open_time"].max() + pd.Timedelta(hours=1)
        out["period_end"] = str(end)
        for strat in STRATEGIES:
            params, in_sample = V.select_params(asset, strat, V.TRAIN_START, V.WF_END)
            ev = V.evaluate_period(asset, strat, params, V.LOCKBOX_START, end)
            ev["params"] = params
            ev["pre_lockbox_in_sample"] = in_sample
            out["results"][f"{strat}|{sym}"] = ev
            m = ev["metrics"]
            print(f"{strat:22s} {sym}  net {m['net_return']:+7.1%}  trades {m['n_trades']:3d}  "
                  f"exp {m['expectancy_per_trade']:+.3%}  B&H {ev['buy_hold']['net_return']:+7.1%}  rnd-pct {ev['percentile_vs_random']:.0f}")
    RESULT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("Lockbox evaluated and locked ->", RESULT.name)


if __name__ == "__main__":
    main()

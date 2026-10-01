"""Data exploration: return distributions, volatility seasonality, moves vs. round-trip cost.

Usage:  python -m src.reports.explore      -> charts + reports/exploration.md
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.engine import DEFAULT_FEE, DEFAULT_SLIPPAGE
from src.data.download import SYMBOLS
from src.data.quality import load

OUT = Path(__file__).resolve().parents[2] / "reports"
ROUND_TRIP = 2 * (DEFAULT_FEE + DEFAULT_SLIPPAGE)  # 0.30%
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    lines = ["# Data exploration", "",
             f"Round-trip cost assumed: {ROUND_TRIP:.2%} (fee {DEFAULT_FEE:.2%} + slippage {DEFAULT_SLIPPAGE:.2%}, per side, x2).", ""]
    dist_rows, move_rows = [], []
    vol_hour, vol_dow = {}, {}

    for s in SYMBOLS:
        h = load(s, "1h").set_index("open_time")
        m5 = load(s, "5m").set_index("open_time")
        r = np.log(h["close"]).diff().dropna()
        r5 = np.log(m5["close"]).diff().dropna()

        dist_rows.append({
            "coin": s, "bars_1h": len(r), "mean_%": r.mean() * 100, "std_%": r.std() * 100,
            "skew": r.skew(), "excess_kurtosis": r.kurt(),
            "p01_%": r.quantile(.01) * 100, "p99_%": r.quantile(.99) * 100,
            "ann_vol_%": r.std() * np.sqrt(365 * 24) * 100,
            "buy_hold_%": (h["close"].iloc[-1] / h["close"].iloc[0] - 1) * 100,
        })
        vol_hour[s] = r.abs().groupby(r.index.hour).mean() * 100
        vol_dow[s] = r.abs().groupby(r.index.dayofweek).mean() * 100

        for label, ret in (("5m", r5), ("1h", r)):
            a = ret.abs()
            move_rows.append({
                "coin": s, "interval": label,
                "median_abs_move_%": a.median() * 100,
                "mean_abs_move_%": a.mean() * 100,
                "share_bars_abs>round_trip": (a > ROUND_TRIP).mean() * 100,
                "share_bars_abs>2x_round_trip": (a > 2 * ROUND_TRIP).mean() * 100,
            })

        # Return histogram
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(r * 100, bins=200, range=(-3, 3), color="#3b6ea5")
        ax.axvline(0, color="k", lw=.5)
        ax.set(title=f"{s} 1h log returns (%, clipped to ±3%)", xlabel="return %", ylabel="bars")
        fig.tight_layout(); fig.savefig(OUT / f"returns_hist_{s}.png", dpi=110); plt.close(fig)

    dist = pd.DataFrame(dist_rows).round(3)
    moves = pd.DataFrame(move_rows).round(3)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    pd.DataFrame(vol_hour).plot(ax=axes[0], marker="o")
    axes[0].set(title="Mean |1h return| by UTC hour", xlabel="hour (UTC)", ylabel="%")
    d = pd.DataFrame(vol_dow); d.index = DAYS
    d.plot.bar(ax=axes[1]); axes[1].set(title="Mean |1h return| by weekday", ylabel="%")
    fig.tight_layout(); fig.savefig(OUT / "volatility_seasonality.png", dpi=110); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    p = moves.pivot(index="coin", columns="interval", values="share_bars_abs>round_trip")
    p.plot.bar(ax=ax)
    ax.set(title=f"Share of bars whose |move| exceeds the {ROUND_TRIP:.2%} round-trip cost", ylabel="% of bars")
    fig.tight_layout(); fig.savefig(OUT / "moves_vs_cost.png", dpi=110); plt.close(fig)

    lines += ["## Return distribution (1h)", "", dist.to_string(index=False), "",
              "## Typical move vs. round-trip cost", "", moves.to_string(index=False), "",
              "## Volatility by hour (UTC), mean |1h return| %", "", pd.DataFrame(vol_hour).round(3).to_string(), "",
              "## Volatility by weekday, mean |1h return| %", "", d.round(3).to_string(), "",
              "Charts: `returns_hist_*.png`, `volatility_seasonality.png`, `moves_vs_cost.png`."]
    (OUT / "exploration.md").write_text("\n".join(lines), encoding="utf-8")
    pd.set_option("display.width", 200, "display.max_columns", 30)
    print(dist.to_string(index=False)); print(); print(moves.to_string(index=False))
    print("\nBy hour:\n", pd.DataFrame(vol_hour).round(3).T.to_string()); print("\nBy weekday:\n", d.round(3).T.to_string())


if __name__ == "__main__":
    main()

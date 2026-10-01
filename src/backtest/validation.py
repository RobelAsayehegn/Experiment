"""Honest validation: train -> expanding walk-forward -> one-shot lockbox.

Periods (UTC, 1h bars):
  TRAIN       2023-10-01 .. 2024-09-30   first 12 months, used only to pick the first parameters
  WALK-FORWARD 2024-10-01 .. 2026-02-28  3-month folds; params re-picked on ALL earlier data each fold
  LOCKBOX     2026-03-01 .. end of data  last 6 months, evaluated exactly once (see run_lockbox)

Parameter selection metric: net Sharpe on the training window (costs included).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest.engine import Result, run_backtest
from src.backtest.metrics import compute_metrics
from src.strategies.baselines import buy_and_hold, random_entries
from src.strategies.registry import STRATEGIES

BARS_PER_YEAR = 365 * 24
TS = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731

TRAIN_START = TS("2023-10-01")
TRAIN_END = TS("2024-10-01")        # exclusive
WF_END = TS("2026-03-01")           # exclusive; also the lockbox start
LOCKBOX_START = WF_END
FOLD_EDGES = [TS(d) for d in ("2024-10-01", "2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-03-01")]


def n_combinations() -> int:
    return sum(len(g) for _, g in STRATEGIES.values())


@dataclass
class Asset:
    symbol: str
    df: pd.DataFrame
    weight_cache: dict

    def weights(self, strat: str, params: dict) -> np.ndarray:
        key = (strat, tuple(sorted(params.items())))
        if key not in self.weight_cache:
            fn, _ = STRATEGIES[strat]
            self.weight_cache[key] = np.asarray(fn(self.df, **params), dtype=float)
        return self.weight_cache[key]

    def mask(self, start, end) -> np.ndarray:
        t = self.df["open_time"]
        return ((t >= start) & (t < end)).to_numpy()

    def run(self, w: np.ndarray, start, end) -> Result:
        m = self.mask(start, end)
        return run_backtest(self.df.loc[m].reset_index(drop=True), w[m], bars_per_year=BARS_PER_YEAR)


def chain(results: list[Result]) -> Result:
    """Stitch consecutive fold results into one compounding result (each fold starts flat)."""
    cap, eqs, trades, poss, fees, slip = 1.0, [], [], [], 0.0, 0.0
    init = results[0].initial_capital
    for r in results:
        eqs.append(r.equity * cap)
        t = r.trades.copy()
        if len(t):
            t["pnl"] = t["pnl"] * cap
        trades.append(t)
        poss.append(r.position)
        fees += r.fees_paid * cap
        slip += r.slippage_paid * cap
        cap = float(eqs[-1].iloc[-1] / init)
    tr = pd.concat([t for t in trades if len(t)], ignore_index=True) if any(len(t) for t in trades) else trades[0]
    return Result(pd.concat(eqs), tr, fees, slip, init, results[0].bars_per_year, pd.concat(poss))


def select_params(asset: Asset, strat: str, start, end) -> tuple[dict, dict]:
    """Best params by net Sharpe on [start, end). Returns (params, metrics_in_sample)."""
    _, grid = STRATEGIES[strat]
    best, best_m, best_s = None, None, -np.inf
    for p in grid:
        m = compute_metrics(asset.run(asset.weights(strat, p), start, end))
        s = m["sharpe"] if m["n_trades"] >= 5 else -np.inf   # ignore configs that barely trade
        if best is None or s > best_s:
            best, best_m, best_s = p, m, s
    return best, best_m


def random_baseline(asset: Asset, start, end, n_trades: int, avg_hold: float, n_sims: int = 200, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    m = asset.mask(start, end)
    sub = asset.df.loc[m].reset_index(drop=True)
    rets, exps = [], []
    for _ in range(n_sims):
        w = random_entries(len(sub), n_trades, avg_hold, rng)
        met = compute_metrics(run_backtest(sub, w, bars_per_year=BARS_PER_YEAR))
        rets.append(met["net_return"])
        exps.append(met["expectancy_per_trade"])
    rets = np.array(rets)
    return {"mean_return": float(rets.mean()), "p05": float(np.percentile(rets, 5)),
            "p95": float(np.percentile(rets, 95)), "returns": rets.tolist(),
            "mean_expectancy": float(np.nanmean(exps))}


def avg_hold_bars(res: Result) -> float:
    n = len(res.trades)
    return float((res.position > 0).sum() / n) if n else 1.0


def evaluate_period(asset: Asset, strat: str, params: dict, start, end, n_sims: int = 200) -> dict:
    """Run one fixed parameter set on one period, with B&H and random baselines for the same period."""
    res = run_backtest_slice(asset, strat, params, start, end)
    met = compute_metrics(res)
    bh = compute_metrics(asset.run(buy_and_hold(asset.df), start, end))
    rnd = random_baseline(asset, start, end, met["n_trades"], avg_hold_bars(res), n_sims)
    pct = float((np.array(rnd["returns"]) < met["net_return"]).mean() * 100)
    return {"metrics": met, "buy_hold": bh, "random": {k: v for k, v in rnd.items() if k != "returns"},
            "percentile_vs_random": pct}


def run_backtest_slice(asset, strat, params, start, end) -> Result:
    return asset.run(asset.weights(strat, params), start, end)

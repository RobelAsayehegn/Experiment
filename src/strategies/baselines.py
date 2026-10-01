"""Baselines: buy-and-hold, and random entries matched to a strategy's trade count."""
from __future__ import annotations

import numpy as np


def buy_and_hold(df) -> np.ndarray:
    """Fully long from the first bar. (The engine buys at bar 1's open and pays costs once.)"""
    return np.ones(len(df))


def random_entries(n_bars: int, n_trades: int, avg_hold: float, rng: np.random.Generator) -> np.ndarray:
    """Random long-only weights with `n_trades` round trips of roughly `avg_hold` bars each.

    Hold lengths are exponential around `avg_hold`; trades are placed at random, non-overlapping
    start points. Used to ask: does the strategy beat luck with the same turnover?
    """
    w = np.zeros(n_bars)
    if n_trades <= 0 or n_bars < 4:
        return w
    avg_hold = max(1.0, avg_hold)
    # Draw hold lengths, then spread the remaining (flat) time randomly across n_trades+1 gaps.
    holds = np.maximum(1, rng.exponential(avg_hold, n_trades).round().astype(int))
    # Scale down if holds don't fit.
    total = holds.sum()
    budget = n_bars - n_trades - 1
    if total > budget:
        holds = np.maximum(1, (holds * budget / total).astype(int))
    free = n_bars - holds.sum() - n_trades  # at least 1 flat bar between trades
    cuts = np.sort(rng.integers(0, max(free, 0) + 1, n_trades))
    gaps = np.diff(np.concatenate([[0], cuts]))
    pos = 0
    for h, g in zip(holds, gaps):
        pos += int(g)
        end = min(n_bars, pos + int(h))
        w[pos:end] = 1.0
        pos = end + 1  # flat bar between trades so they stay distinct
        if pos >= n_bars:
            break
    return w

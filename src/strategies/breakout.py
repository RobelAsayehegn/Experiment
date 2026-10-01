"""Donchian-style breakout: buy a close above the prior N-bar high, exit below the prior M-bar low."""
from __future__ import annotations

from .indicators import hold_between

NAME = "breakout"
GRID = [{"entry_n": n, "exit_n": m} for n in (24, 72, 168, 336) for m in (12, 24, 72) if m <= n]


def weights(df, entry_n: int, exit_n: int):
    c, h, l = df["close"], df["high"], df["low"]
    # shift(1): compare today's close with the range that ended BEFORE today.
    enter = c > h.rolling(entry_n).max().shift(1)
    exit_ = c < l.rolling(exit_n).min().shift(1)
    return hold_between(enter.to_numpy(), exit_.to_numpy())

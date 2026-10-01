"""Donchian-style breakout: buy a close above the prior N-bar high, exit below the prior M-bar low.
With side='both', a close below the prior N-bar low goes short, covered above the prior M-bar high."""
from __future__ import annotations

from .indicators import hold_between, hold_long_short

NAME = "breakout"
GRID = [{"entry_n": n, "exit_n": m} for n in (24, 72, 168, 336) for m in (12, 24, 72) if m <= n]


def weights(df, entry_n: int, exit_n: int, side: str = "long"):
    c, h, l = df["close"], df["high"], df["low"]
    # shift(1): compare this close with the range that ended BEFORE this bar.
    up_break = c > h.rolling(entry_n).max().shift(1)
    dn_exit = c < l.rolling(exit_n).min().shift(1)
    if side == "long":
        return hold_between(up_break.to_numpy(), dn_exit.to_numpy())
    dn_break = c < l.rolling(entry_n).min().shift(1)
    up_exit = c > h.rolling(exit_n).max().shift(1)
    return hold_long_short(up_break.to_numpy(), dn_exit.to_numpy(), dn_break.to_numpy(), up_exit.to_numpy())

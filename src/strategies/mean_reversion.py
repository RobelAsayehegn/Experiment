"""Mean reversion, two variants kept side by side: RSI extremes and Bollinger bands.
side='both' mirrors the rules for shorts (sell overbought / upper band, cover at the mean)."""
from __future__ import annotations

from .indicators import hold_between, hold_long_short, rsi, sma

NAME_RSI = "rsi_reversion"
GRID_RSI = [{"n": 14, "entry": e, "exit": x} for e in (20, 25, 30) for x in (50, 60)]

NAME_BB = "bollinger_reversion"
GRID_BB = [{"n": n, "k": k} for n in (20, 50) for k in (2.0, 2.5)]


def weights_rsi(df, n: int, entry: float, exit: float, side: str = "long"):
    r = rsi(df["close"], n)
    el, xl = (r < entry).to_numpy(), (r > exit).to_numpy()
    if side == "long":
        return hold_between(el, xl)
    return hold_long_short(el, xl, (r > 100 - entry).to_numpy(), (r < 100 - exit).to_numpy())


def weights_bb(df, n: int, k: float, side: str = "long"):
    c = df["close"]
    mid = sma(c, n)
    sd = c.rolling(n).std()
    el, xl = (c < mid - k * sd).to_numpy(), (c > mid).to_numpy()
    if side == "long":
        return hold_between(el, xl)
    return hold_long_short(el, xl, (c > mid + k * sd).to_numpy(), (c < mid).to_numpy())

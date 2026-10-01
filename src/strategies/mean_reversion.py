"""Mean reversion, two variants kept side by side: RSI oversold and Bollinger lower-band."""
from __future__ import annotations

from .indicators import hold_between, rsi, sma

NAME_RSI = "rsi_reversion"
GRID_RSI = [{"n": 14, "entry": e, "exit": x} for e in (20, 25, 30) for x in (50, 60)]

NAME_BB = "bollinger_reversion"
GRID_BB = [{"n": n, "k": k} for n in (20, 50) for k in (2.0, 2.5)]


def weights_rsi(df, n: int, entry: float, exit: float):
    r = rsi(df["close"], n)
    return hold_between((r < entry).to_numpy(), (r > exit).to_numpy())


def weights_bb(df, n: int, k: float):
    c = df["close"]
    mid = sma(c, n)
    sd = c.rolling(n).std()
    return hold_between((c < mid - k * sd).to_numpy(), (c > mid).to_numpy())

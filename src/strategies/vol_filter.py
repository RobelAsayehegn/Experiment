"""Volatility filter + trend: take the MA-trend signal only when realised volatility is calm.

"Calm" = current 24-bar volatility is below its trailing q-quantile over the past `lookback` bars
(trailing only, so no look-ahead). side='both' also shorts calm downtrends.
"""
from __future__ import annotations

import numpy as np

from .indicators import realized_vol, sma

NAME = "vol_filtered_trend"
GRID = [{"fast": f, "slow": s, "q": q} for f, s in ((20, 100), (50, 200)) for q in (0.5, 0.7, 0.9)]


def weights(df, fast: int, slow: int, q: float, vol_n: int = 24, lookback: int = 720, side: str = "long") -> np.ndarray:
    c = df["close"]
    f, s = sma(c, fast), sma(c, slow)
    vol = realized_vol(c, vol_n)
    calm = (vol <= vol.rolling(lookback).quantile(q)).to_numpy()
    up = ((f > s).to_numpy() & calm).astype(float)
    if side == "long":
        return up
    return up - ((f < s).to_numpy() & calm).astype(float)

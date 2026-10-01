"""Moving-average trend following: long while fast SMA > slow SMA (short while below, if side='both')."""
from __future__ import annotations

import numpy as np

from .indicators import sma

NAME = "ma_trend"
GRID = [{"fast": f, "slow": s} for f in (10, 20, 50) for s in (50, 100, 200) if f < s]


def weights(df, fast: int, slow: int, side: str = "long") -> np.ndarray:
    c = df["close"]
    f, s = sma(c, fast), sma(c, slow)
    up = (f > s).to_numpy(dtype=float)
    if side == "long":
        return up
    down = (f < s).to_numpy(dtype=float)
    return up - down

"""Moving-average trend following: long while fast SMA > slow SMA."""
from __future__ import annotations

import numpy as np

from .indicators import sma

NAME = "ma_trend"
GRID = [{"fast": f, "slow": s} for f in (10, 20, 50) for s in (50, 100, 200) if f < s]


def weights(df, fast: int, slow: int) -> np.ndarray:
    c = df["close"]
    return (sma(c, fast) > sma(c, slow)).to_numpy(dtype=float)

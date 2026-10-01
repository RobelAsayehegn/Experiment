"""Small indicator helpers. Every value at bar t uses data up to and including bar t's close."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def realized_vol(close: pd.Series, n: int) -> pd.Series:
    return close.pct_change().rolling(n).std()


def hold_between(enter: np.ndarray, exit_: np.ndarray) -> np.ndarray:
    """Stateful 0/1 position: go long when `enter` fires while flat, go flat when `exit_` fires
    while long. Exit is checked first. NaN conditions count as False."""
    enter = np.nan_to_num(np.asarray(enter, dtype=float)).astype(bool)
    exit_ = np.nan_to_num(np.asarray(exit_, dtype=float)).astype(bool)
    pos = np.zeros(len(enter))
    state = 0.0
    for i in range(len(enter)):
        if state == 1.0 and exit_[i]:
            state = 0.0
        elif state == 0.0 and enter[i]:
            state = 1.0
        pos[i] = state
    return pos

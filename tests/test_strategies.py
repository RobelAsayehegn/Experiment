import numpy as np
import pandas as pd
import pytest

from src.strategies.baselines import random_entries
from src.strategies.registry import STRATEGIES


def synthetic(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(rng.normal(0, 0.01, n).cumsum())
    open_ = np.concatenate([[100], close[:-1]])
    high = np.maximum(open_, close) * (1 + rng.random(n) * 0.005)
    low = np.minimum(open_, close) * (1 - rng.random(n) * 0.005)
    t = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"open_time": t, "open": open_, "high": high, "low": low, "close": close})


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategy_has_no_lookahead(name):
    fn, grid = STRATEGIES[name]
    df = synthetic()
    k = 2000
    df2 = df.copy()
    df2.loc[k:, ["open", "high", "low", "close"]] *= np.random.default_rng(5).uniform(0.5, 2, (len(df) - k, 1))
    for params in grid:
        a = np.asarray(fn(df, **params))
        b = np.asarray(fn(df2, **params))
        assert np.array_equal(a[:k], b[:k]), f"{name} {params} uses future data"


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategy_weights_valid(name):
    fn, grid = STRATEGIES[name]
    df = synthetic()
    for params in grid:
        w = np.asarray(fn(df, **params))
        assert len(w) == len(df)
        assert set(np.unique(w)) <= ({-1.0, 0.0, 1.0} if name.endswith("_ls") else {0.0, 1.0})


def test_random_entries_shape():
    rng = np.random.default_rng(0)
    w = random_entries(5000, 40, 20, rng)
    assert len(w) == 5000 and set(np.unique(w)) <= {0.0, 1.0}
    starts = ((w[1:] == 1) & (w[:-1] == 0)).sum() + int(w[0] == 1)
    assert 30 <= starts <= 40


@pytest.mark.parametrize("name", [n for n in STRATEGIES if n.endswith("_ls")])
def test_ls_variant_goes_both_ways(name):
    fn, grid = STRATEGIES[name]
    w = np.asarray(fn(synthetic(6000, seed=2), **grid[0]))
    assert (w < 0).any() and (w > 0).any()

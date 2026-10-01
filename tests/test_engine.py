import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.backtest.metrics import compute_metrics


def make_df(opens, closes=None):
    opens = np.asarray(opens, dtype=float)
    closes = opens if closes is None else np.asarray(closes, dtype=float)
    t = pd.date_range("2024-01-01", periods=len(opens), freq="1h", tz="UTC")
    return pd.DataFrame({"open_time": t, "open": opens, "close": closes})


def test_no_trades_equity_flat():
    df = make_df([100, 110, 120, 130])
    res = run_backtest(df, np.zeros(4))
    assert (res.equity == 10_000).all()
    assert len(res.trades) == 0 and res.fees_paid == 0


def test_round_trip_flat_price_loses_exactly_costs():
    fee, slip = 0.001, 0.0005
    df = make_df([100] * 6)
    w = np.array([1, 1, 0, 0, 0, 0])  # signal at bar0 -> buy open1; signal bar2 -> sell open3
    res = run_backtest(df, w, fee=fee, slippage=slip)
    # Buy: q = C / (p(1+s)(1+f)); sell: C' = q p (1-s)(1-f)
    expected = 10_000 * (1 - slip) * (1 - fee) / ((1 + slip) * (1 + fee))
    assert res.equity.iloc[-1] == pytest.approx(expected, rel=1e-12)
    assert len(res.trades) == 1
    assert res.trades["pnl"].iloc[0] == pytest.approx(expected - 10_000, rel=1e-9)
    assert res.fees_paid > 0 and res.slippage_paid > 0


def test_zero_costs_flat_price_no_loss():
    df = make_df([100] * 6)
    res = run_backtest(df, np.array([1, 1, 0, 0, 0, 0]), fee=0, slippage=0)
    assert res.equity.iloc[-1] == pytest.approx(10_000)


def test_fees_scale_with_traded_notional():
    df = make_df([100] * 6)
    res = run_backtest(df, np.array([1, 1, 0, 0, 0, 0]), fee=0.002, slippage=0)
    # fee on buy (~20) and sell (~20)
    assert res.fees_paid == pytest.approx(10_000 * 0.002 / 1.002 + 10_000 / 1.002 * 0.002, rel=1e-9)


def test_next_bar_open_execution():
    # Signal at close of bar 1 -> buy at open of bar 2 (price 200), not bar 1's close (150).
    opens = [100, 100, 200, 400, 400]
    closes = [100, 150, 300, 400, 400]
    df = make_df(opens, closes)
    res = run_backtest(df, np.array([0, 1, 1, 1, 1]), fee=0, slippage=0)
    # bought at 200, last close 400 -> equity doubles
    assert res.equity.iloc[-1] == pytest.approx(20_000)
    # bar 1 equity unaffected by the signal that fires at its close
    assert res.equity.iloc[1] == pytest.approx(10_000)


def test_no_lookahead_future_data_does_not_change_past_equity():
    rng = np.random.default_rng(0)
    opens = 100 + rng.normal(0, 1, 200).cumsum()
    closes = opens + rng.normal(0, 0.3, 200)
    w = (rng.random(200) > 0.5).astype(float)
    base = run_backtest(make_df(opens, closes), w).equity.to_numpy()

    k = 120
    opens2, closes2, w2 = opens.copy(), closes.copy(), w.copy()
    opens2[k:] *= 3; closes2[k:] *= 3; w2[k:] = 1 - w2[k:]   # change everything from bar k onward
    alt = run_backtest(make_df(opens2, closes2), w2).equity.to_numpy()
    # bars before k are identical; bar k's open trade uses w[k-1], unchanged
    assert np.allclose(base[:k], alt[:k])


def test_signal_on_last_bar_never_trades():
    df = make_df([100, 100, 100, 100])
    res = run_backtest(df, np.array([0, 0, 0, 1]))
    assert len(res.trades) == 0 and res.fees_paid == 0


def test_open_position_liquidated_at_end_with_costs():
    df = make_df([100] * 5)
    res = run_backtest(df, np.array([1, 1, 1, 1, 1]), fee=0.001, slippage=0.0)
    assert len(res.trades) == 1
    assert res.equity.iloc[-1] < 10_000  # paid buy + sell fees
    assert res.fees_paid == pytest.approx(10_000 - res.equity.iloc[-1], rel=1e-9)


def test_never_spends_more_than_cash_and_equity_accounting():
    rng = np.random.default_rng(1)
    opens = 100 + rng.normal(0, 1, 500).cumsum() + 50
    closes = opens + rng.normal(0, 0.2, 500)
    w = rng.random(500)
    res = run_backtest(make_df(opens, closes), w)
    assert (res.equity > 0).all()
    assert res.position.between(0, 1 + 1e-9).all()
    # Sum of round-trip pnl equals total change in equity (everything liquidated at end)
    assert res.trades["pnl"].sum() == pytest.approx(res.equity.iloc[-1] - 10_000, rel=1e-9)


def test_metrics_basic():
    df = make_df([100, 100, 110, 110, 100, 100, 100])
    # win: buy 100 sell 110 ; loss afterwards
    w = np.array([1, 1, 0, 0, 0, 0, 0])
    res = run_backtest(df, w, fee=0, slippage=0)
    m = compute_metrics(res)
    assert m["n_trades"] == 1
    assert m["win_rate"] == 1.0
    assert m["net_return"] == pytest.approx(0.10)
    assert m["expectancy_per_trade"] == pytest.approx(0.10)
    assert m["max_drawdown"] == pytest.approx(0.0)

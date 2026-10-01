"""Long-only spot backtest engine with fees, slippage and next-bar execution.

Conventions (see CLAUDE.md):
- `weights[t]` is the desired fraction of equity to hold, decided using information up to and
  including the CLOSE of bar t. It is executed at the OPEN of bar t+1. A signal on the last bar
  can never trade.
- Buys fill at open*(1+slippage), sells at open*(1-slippage); the fee is charged on the traded
  notional at the fill price. Costs are per side.
- Spot, long-only: weights are clipped to [0, 1]. No leverage, no shorting.
- Trading happens only when the target weight changes (no constant rebalancing).
- Any open position is liquidated (with costs) at the last bar's close so it shows up as a trade.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DEFAULT_FEE = 0.0010       # 0.10% per side
DEFAULT_SLIPPAGE = 0.0005  # 0.05% per side


@dataclass
class Result:
    equity: pd.Series                 # marked to market at each bar's close
    trades: pd.DataFrame              # one row per round trip
    fees_paid: float                  # fee cash paid
    slippage_paid: float              # approximate cash lost to slippage
    initial_capital: float
    bars_per_year: float
    position: pd.Series = field(default_factory=pd.Series)  # fraction of equity held after each bar's close


def run_backtest(
    df: pd.DataFrame,
    weights: pd.Series | np.ndarray,
    fee: float = DEFAULT_FEE,
    slippage: float = DEFAULT_SLIPPAGE,
    initial_capital: float = 10_000.0,
    bars_per_year: float = 365 * 24,
) -> Result:
    """df needs `open` and `close` columns (index/`open_time` only used for labelling)."""
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    w = np.clip(np.nan_to_num(np.asarray(weights, dtype=float), nan=0.0), 0.0, 1.0)
    if len(w) != n:
        raise ValueError("weights must have the same length as df")

    cash = initial_capital
    units = 0.0
    fees_paid = 0.0
    slip_paid = 0.0
    equity = np.empty(n)
    held = np.zeros(n)
    cur_target = 0.0

    trades = []
    t_open_idx = None
    t_cash_out = 0.0   # cash spent on buys in this round trip (incl. costs)
    t_cash_in = 0.0    # cash received from sells (net of costs)
    t_peak_notional = 0.0

    def do_trade(i: int, px_open: float, target: float):
        nonlocal cash, units, fees_paid, slip_paid, t_open_idx, t_cash_out, t_cash_in, t_peak_notional
        eq = cash + units * px_open
        cur_val = units * px_open
        want = target * eq
        if want > cur_val:  # buy
            buy_px = px_open * (1 + slippage)
            spend = min(want - cur_val, cash)            # cash used, fee included
            q = spend / (buy_px * (1 + fee))
            fee_cash = q * buy_px * fee
            cash -= spend
            units += q
            fees_paid += fee_cash
            slip_paid += q * (buy_px - px_open)
            if t_open_idx is None:
                t_open_idx = i
                t_cash_out = t_cash_in = t_peak_notional = 0.0
            t_cash_out += spend
            t_peak_notional = max(t_peak_notional, units * px_open)
        elif want < cur_val:  # sell
            sell_px = px_open * (1 - slippage)
            q = min((cur_val - want) / px_open, units)
            if target == 0.0:
                q = units
            gross = q * sell_px
            fee_cash = gross * fee
            cash += gross - fee_cash
            units -= q
            if units < 1e-12:
                units = 0.0
            fees_paid += fee_cash
            slip_paid += q * (px_open - sell_px)
            t_cash_in += gross - fee_cash
            if units == 0.0 and t_open_idx is not None:
                trades.append((t_open_idx, i, t_cash_out, t_cash_in))
                t_open_idx = None

    for i in range(n):
        if i > 0 and w[i - 1] != cur_target:       # signal from previous close -> this open
            do_trade(i, opens[i], w[i - 1])
            cur_target = w[i - 1]
        equity[i] = cash + units * closes[i]
        held[i] = (units * closes[i] / equity[i]) if equity[i] > 0 else 0.0

    if units > 0:  # liquidate at the final close, with costs
        sell_px = closes[-1] * (1 - slippage)
        gross = units * sell_px
        fee_cash = gross * fee
        fees_paid += fee_cash
        slip_paid += units * (closes[-1] - sell_px)
        cash += gross - fee_cash
        t_cash_in += gross - fee_cash
        units = 0.0
        equity[-1] = cash
        trades.append((t_open_idx, n - 1, t_cash_out, t_cash_in))

    times = df["open_time"] if "open_time" in df.columns else df.index
    tdf = pd.DataFrame(trades, columns=["entry_i", "exit_i", "cash_out", "cash_in"])
    if len(tdf):
        tdf["entry_time"] = np.asarray(times)[tdf["entry_i"].to_numpy()]
        tdf["exit_time"] = np.asarray(times)[tdf["exit_i"].to_numpy()]
        tdf["pnl"] = tdf["cash_in"] - tdf["cash_out"]          # net of all costs
        tdf["ret"] = tdf["pnl"] / tdf["cash_out"]              # net return on cash deployed
    else:
        tdf = pd.DataFrame(columns=list(tdf.columns) + ["entry_time", "exit_time", "pnl", "ret"])

    return Result(
        equity=pd.Series(equity, index=pd.Index(np.asarray(times), name="time")),
        trades=tdf,
        fees_paid=fees_paid,
        slippage_paid=slip_paid,
        initial_capital=initial_capital,
        bars_per_year=bars_per_year,
        position=pd.Series(held, index=pd.Index(np.asarray(times), name="time")),
    )

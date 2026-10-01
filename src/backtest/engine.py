"""Long/short backtest engine with fees, slippage and next-bar execution.

Conventions (see CLAUDE.md):
- `weights[t]` in [-1, 1] is the desired exposure as a fraction of equity (+ long, - short),
  decided using information up to and including the CLOSE of bar t. It is executed at the OPEN of
  bar t+1. A signal on the last bar can never trade.
- Buys fill at open*(1+slippage), sells at open*(1-slippage); the fee is charged on the traded
  notional at the fill price. Costs are per side. Flipping long->short pays both legs.
- No leverage: |weight| <= 1. Shorts are NOT available on Binance spot; they are modelled like a
  perpetual future / margin short on the same price series: same fees/slippage plus a holding cost
  `short_cost_per_bar` charged on short notional every bar (funding/borrow proxy).
- Trading happens only when the target weight changes (no constant rebalancing).
- Any open position is closed (with costs) at the last bar's close so it shows up as a trade.
- If equity is wiped out the account is closed and stays flat.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DEFAULT_FEE = 0.0010       # 0.10% per side
DEFAULT_SLIPPAGE = 0.0005  # 0.05% per side
# ~0.01% per 8h (typical perp funding / cheap margin borrow) = 0.00125% per hour.
DEFAULT_SHORT_COST_PER_HOUR = 0.0001 / 8


@dataclass
class Result:
    equity: pd.Series                 # marked to market at each bar's close
    trades: pd.DataFrame              # one row per round trip (flat -> flat)
    fees_paid: float                  # fee cash paid
    slippage_paid: float              # approximate cash lost to slippage
    initial_capital: float
    bars_per_year: float
    position: pd.Series = field(default_factory=pd.Series)  # signed exposure / equity after each bar's close
    financing_paid: float = 0.0       # short holding cost


def run_backtest(
    df: pd.DataFrame,
    weights: pd.Series | np.ndarray,
    fee: float = DEFAULT_FEE,
    slippage: float = DEFAULT_SLIPPAGE,
    initial_capital: float = 10_000.0,
    bars_per_year: float = 365 * 24,
    short_cost_per_hour: float = DEFAULT_SHORT_COST_PER_HOUR,
) -> Result:
    """df needs `open` and `close` columns (`open_time` only used for labelling)."""
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    w = np.clip(np.nan_to_num(np.asarray(weights, dtype=float), nan=0.0), -1.0, 1.0)
    if len(w) != n:
        raise ValueError("weights must have the same length as df")
    bar_hours = 365 * 24 / bars_per_year
    short_cost = short_cost_per_hour * bar_hours

    s = {"cash": initial_capital, "units": 0.0, "fees": 0.0, "slip": 0.0, "fin": 0.0,
         "t_start": None, "t_flow": 0.0, "t_open": 0.0}
    trades: list[tuple] = []
    equity = np.empty(n)
    held = np.zeros(n)

    def trade_to(i: int, px: float, target: float) -> None:
        """Move exposure to `target` (fraction of equity) at open price px, same side only."""
        eq = s["cash"] + s["units"] * px
        want = target * eq
        cur = s["units"] * px
        if want == cur:
            return
        if want > cur:  # buy
            bpx = px * (1 + slippage)
            q = (want - cur) / (bpx * (1 + fee))
            if s["units"] < 0 and target <= 0:      # covering a short: never buy more than the short
                q = -s["units"] if target == 0 else min(q, -s["units"])
            gross = q * bpx
            f = gross * fee
            s["cash"] -= gross + f
            s["fees"] += f
            s["slip"] += q * (bpx - px)
            flow = -(gross + f)
            if s["units"] >= 0 and q > 0:
                s["t_open"] += gross + f
            s["units"] += q
        else:  # sell
            spx = px * (1 - slippage)
            q = (cur - want) / px
            if s["units"] > 0 and target >= 0:
                q = s["units"] if target == 0 else min(q, s["units"])
            gross = q * spx
            f = gross * fee
            s["cash"] += gross - f
            s["fees"] += f
            s["slip"] += q * (px - spx)
            flow = gross - f
            if s["units"] <= 0 and q > 0:
                s["t_open"] += gross - f
            s["units"] -= q
        if abs(s["units"]) < 1e-12:
            s["units"] = 0.0
        if s["t_start"] is None:
            s["t_start"], s["t_flow"], s["t_open"] = i, 0.0, abs(flow)
        s["t_flow"] += flow
        if s["units"] == 0.0:
            trades.append((s["t_start"], i, s["t_flow"], s["t_open"]))
            s["t_start"] = None

    def move(i: int, px: float, target: float) -> None:
        cur_sign = np.sign(s["units"])
        if cur_sign != 0 and target != 0 and np.sign(target) != cur_sign:
            trade_to(i, px, 0.0)         # close first, then open the other side
        trade_to(i, px, target)

    dead = False
    cur_target = 0.0
    for i in range(n):
        if not dead and i > 0 and w[i - 1] != cur_target:
            move(i, opens[i], w[i - 1])
            cur_target = w[i - 1]
        if s["units"] < 0:               # short holding cost on notional, charged at the close
            c = -s["units"] * closes[i] * short_cost
            s["cash"] -= c
            s["fin"] += c
            s["t_flow"] -= c
        eq_i = s["cash"] + s["units"] * closes[i]
        if eq_i <= 0 and not dead:       # wiped out: close the account
            dead = True
            eq_i = 0.0
            s["cash"], s["units"] = 0.0, 0.0
            if s["t_start"] is not None:
                trades.append((s["t_start"], i, -s["t_open"], s["t_open"]))
                s["t_start"] = None
        equity[i] = 0.0 if dead else eq_i
        held[i] = (s["units"] * closes[i] / equity[i]) if equity[i] > 0 else 0.0

    if s["units"] != 0:                  # close at the final close, with costs
        last = closes[-1]
        if s["units"] > 0:
            px = last * (1 - slippage)
            gross = s["units"] * px
            f = gross * fee
            s["cash"] += gross - f
            flow = gross - f
            s["slip"] += s["units"] * (last - px)
        else:
            px = last * (1 + slippage)
            q = -s["units"]
            gross = q * px
            f = gross * fee
            s["cash"] -= gross + f
            flow = -(gross + f)
            s["slip"] += q * (px - last)
        s["fees"] += f
        s["t_flow"] += flow
        s["units"] = 0.0
        equity[-1] = s["cash"]
        trades.append((s["t_start"], n - 1, s["t_flow"], s["t_open"]))

    times = df["open_time"] if "open_time" in df.columns else df.index
    tarr = np.asarray(times)
    tdf = pd.DataFrame(trades, columns=["entry_i", "exit_i", "pnl", "open_notional"])
    if len(tdf):
        tdf["entry_time"] = tarr[tdf["entry_i"].to_numpy()]
        tdf["exit_time"] = tarr[tdf["exit_i"].to_numpy()]
        tdf["ret"] = tdf["pnl"] / tdf["open_notional"]          # net return on notional opened
        tdf["side"] = "long"  # filled below
    else:
        tdf = pd.DataFrame(columns=list(tdf.columns) + ["entry_time", "exit_time", "ret", "side"])
    # side of each trade from the exposure held at the end of its first bar
    if len(tdf):
        first_pos = held[np.minimum(tdf["entry_i"].to_numpy(), n - 1)]
        tdf["side"] = np.where(first_pos < 0, "short", "long")

    idx = pd.Index(tarr, name="time")
    return Result(
        equity=pd.Series(equity, index=idx), trades=tdf, fees_paid=s["fees"], slippage_paid=s["slip"],
        initial_capital=initial_capital, bars_per_year=bars_per_year, position=pd.Series(held, index=idx),
        financing_paid=s["fin"],
    )

"""Performance metrics. Everything is computed on net-of-cost equity and trades."""
from __future__ import annotations

import numpy as np

from .engine import Result


def compute_metrics(res: Result) -> dict:
    eq = res.equity
    rets = eq.pct_change().fillna(0.0)
    std = rets.std()
    sharpe = float(rets.mean() / std * np.sqrt(res.bars_per_year)) if std > 0 else 0.0
    dd = eq / eq.cummax() - 1.0

    t = res.trades
    n = len(t)
    wins = t[t["pnl"] > 0] if n else t
    losses = t[t["pnl"] <= 0] if n else t
    gross_win = float(wins["pnl"].sum()) if n else 0.0
    gross_loss = float(-losses["pnl"].sum()) if n else 0.0

    return {
        "net_return": float(eq.iloc[-1] / res.initial_capital - 1.0),
        "max_drawdown": float(dd.min()),
        "sharpe": sharpe,
        "n_trades": n,
        "win_rate": float(len(wins) / n) if n else float("nan"),
        "avg_win": float(wins["ret"].mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses["ret"].mean()) if len(losses) else float("nan"),
        "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else float("nan")),
        "expectancy_per_trade": float(t["ret"].mean()) if n else float("nan"),  # net of costs
        "fees_paid": float(res.fees_paid),
        "slippage_paid": float(res.slippage_paid),
        "time_in_market": float((res.position > 0).mean()),
    }

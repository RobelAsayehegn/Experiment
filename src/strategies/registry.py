"""All strategies in one place: variant name -> (weights function, parameter grid).

Every strategy exists as a long-only variant and a long/short variant ('<name>_ls').
"""
from functools import partial

from . import breakout, ma_trend, mean_reversion, vol_filter

DESCRIPTIONS = {
    "ma_trend": "Trend following. Long while the fast moving average is above the slow one; the long/short version goes short while it is below.",
    "breakout": "Donchian breakout. Buy a close above the prior N-bar high and exit under the prior M-bar low; long/short also sells breakdowns below the N-bar low and covers above the M-bar high.",
    "rsi_reversion": "Mean reversion. Buy when RSI is oversold and exit when it recovers; long/short also sells overbought RSI (mirrored levels) and covers on the way back.",
    "bollinger_reversion": "Mean reversion. Buy when price closes below the lower Bollinger band and exit at the middle band; long/short also sells above the upper band.",
    "vol_filtered_trend": "Trend following that only trades when recent volatility is calm (below its trailing quantile); long/short also shorts calm downtrends.",
}

_BASE = {
    "ma_trend": (ma_trend.weights, ma_trend.GRID),
    "breakout": (breakout.weights, breakout.GRID),
    "rsi_reversion": (mean_reversion.weights_rsi, mean_reversion.GRID_RSI),
    "bollinger_reversion": (mean_reversion.weights_bb, mean_reversion.GRID_BB),
    "vol_filtered_trend": (vol_filter.weights, vol_filter.GRID),
}

STRATEGIES = {}
for _name, (_fn, _grid) in _BASE.items():
    STRATEGIES[_name] = (partial(_fn, side="long"), _grid)
    STRATEGIES[_name + "_ls"] = (partial(_fn, side="both"), _grid)


def base_name(variant: str) -> str:
    return variant[:-3] if variant.endswith("_ls") else variant

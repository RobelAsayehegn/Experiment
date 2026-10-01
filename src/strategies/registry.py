"""All strategies in one place: name -> (weights function, parameter grid)."""
from . import breakout, ma_trend, mean_reversion, vol_filter

STRATEGIES = {
    ma_trend.NAME: (ma_trend.weights, ma_trend.GRID),
    breakout.NAME: (breakout.weights, breakout.GRID),
    mean_reversion.NAME_RSI: (mean_reversion.weights_rsi, mean_reversion.GRID_RSI),
    mean_reversion.NAME_BB: (mean_reversion.weights_bb, mean_reversion.GRID_BB),
    vol_filter.NAME: (vol_filter.weights, vol_filter.GRID),
}

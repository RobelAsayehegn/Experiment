I want to build a Python research project that tests whether any simple trading strategy has
a real edge on Binance spot data after fees. Read CLAUDE.md first and follow its rules.
This is phase 1: research and backtesting only, with no API keys and no orders.

Please do the following, step by step, and check in with me after each milestone:

1. Project setup
   - Create a Python virtual environment, `requirements.txt` (pandas, numpy, pyarrow,
     requests, matplotlib, pytest), `.gitignore` (data/, .venv/, .env), and a short README.
   - Suggested layout: `src/data/`, `src/backtest/`, `src/strategies/`, `src/reports/`, `tests/`.

2. Historical data downloader
   - Download monthly kline (candlestick) files from Binance's public archive
     (https://data.binance.vision) for BTCUSDT, ETHUSDT and SOLUSDT, at the 5m and 1h intervals,
     covering roughly the last 3 years.
   - Verify each file against its CHECKSUM, merge the files, and save them as Parquet.
   - Check data quality: missing candles, duplicates, gaps. Print a short summary.

3. Data exploration
   - For each coin: returns distribution, volatility by hour of day and day of week,
     typical spread of moves vs. the round-trip fee (~0.2–0.3% with slippage).
   - Save charts to `reports/`. Tell me in plain language what the data shows.

4. Backtest engine
   - Simple, readable, event-by-event or vectorized engine with: fees per side, slippage,
     next-bar execution (no look-ahead), position sizing, and an equity curve.
   - Metrics: net return, max drawdown, Sharpe, number of trades, win rate,
     average win/loss, profit factor, expectancy per trade after costs, total fees paid.
   - Write pytest tests proving fees are applied and there is no look-ahead.

5. Baselines and strategies
   - Baselines: buy-and-hold, and random entries with the same trade count.
   - Test a few classic, simple hypotheses (keep each in its own file):
     moving-average trend following, breakout of recent highs, mean reversion (RSI or
     Bollinger), and a volatility filter combined with one of these.

6. Honest validation
   - Split data into: training period, walk-forward validation, and the last 6 months as a
     lockbox evaluated only once at the end.
   - Use small parameter grids and report how many combinations were tried (to spot
     overfitting). Show how results change across coins and time periods.

7. Report
   - Generate a single summary report (Markdown or HTML) comparing every strategy with the
     baselines after costs, on validation and lockbox data.
   - End with a plain-language verdict: is there evidence of an edge, how strong, how
     confident, and what the main risks are. "No edge found" is an acceptable answer.

Important: I care about positive expectancy after fees on unseen data, not win rate. A
strategy can win 80% of trades and still lose money. Do not move to testnet or any live
trading. I will decide on next steps after reading the report.

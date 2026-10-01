# Crypto Research Lab: Phase 1 report

## Setup

- Data: Binance spot, public archive, BTC, ETH, SOL, 1h candles, 2023-10-01 to 2026-08-31. Checksums verified, no gaps/duplicates.
- Costs on every trade: fee 0.10% + slippage 0.05% per side (round trip 0.30%). Long-only, fully invested when in a trade, signal on bar t executes at bar t+1 open.
- Periods: **train** 2023-10-01 to 2024-10-01; **walk-forward** 2024-10-01 to 2026-03-01 (3-month folds, parameters re-chosen on all earlier data before each fold, chosen by net Sharpe); **lockbox** last 6 months, evaluated once.
- Parameter combinations tried: **35 per coin** (105 strategy/coin configurations) across 5 strategies. Small grids on purpose; with this many tries a few 'good looking' results are expected by luck alone.
- 'Beats random %' = share of 200 random-entry runs (same trade count and average holding time, same costs) that the strategy out-earned. ~50 is luck, >=95 is notable.

## 1. Walk-forward validation (unseen data, parameters re-picked each fold)

### By strategy (average over BTC/ETH/SOL)

| strategy | avg net return (3 coins) | avg buy&hold | coins profitable | avg expectancy/trade | total trades | avg beats-random % |
|---|---|---|---|---|---|---|
| ma_trend | -30.6% | -21.9% | 0/3 | -0.23% | 271 | 53 |
| breakout | -7.1% | -21.9% | 1/3 | +0.33% | 102 | 56 |
| rsi_reversion | -10.4% | -21.9% | 1/3 | -0.01% | 112 | 62 |
| bollinger_reversion | -40.1% | -21.9% | 0/3 | -0.36% | 382 | 42 |
| vol_filtered_trend | -21.0% | -21.9% | 0/3 | -0.13% | 259 | 63 |

### Every strategy x coin

| strategy | coin | net return | buy&hold | random (mean) | beats random % | trades | win rate | expectancy/trade | profit factor | Sharpe | max DD | fees paid $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ma_trend | BTC | -13.5% | +5.1% | -13.7% | 58 | 76 | 34% | -0.08% | 0.90 | -0.16 | -41.0% | 1680 |
| breakout | BTC | -10.0% | +5.1% | -6.1% | 50 | 36 | 25% | -0.06% | 0.89 | -0.12 | -39.6% | 865 |
| rsi_reversion | BTC | +6.5% | +5.1% | -3.9% | 80 | 18 | 72% | +0.43% | 1.28 | 0.34 | -17.3% | 355 |
| bollinger_reversion | BTC | -33.5% | +5.1% | -27.4% | 40 | 108 | 61% | -0.34% | 0.67 | -0.87 | -42.5% | 1988 |
| vol_filtered_trend | BTC | -21.9% | +5.1% | -24.1% | 57 | 115 | 37% | -0.18% | 0.83 | -0.49 | -40.2% | 2357 |
| ma_trend | ETH | -39.8% | -25.2% | -22.2% | 38 | 87 | 26% | -0.33% | 0.77 | -0.57 | -62.0% | 1530 |
| breakout | ETH | +16.0% | -25.2% | -3.0% | 76 | 19 | 42% | +1.47% | 1.17 | 0.49 | -35.5% | 485 |
| rsi_reversion | ETH | -5.0% | -25.2% | -5.7% | 57 | 25 | 60% | -0.04% | 0.90 | 0.05 | -29.2% | 459 |
| bollinger_reversion | ETH | -44.5% | -25.2% | -42.6% | 53 | 183 | 62% | -0.26% | 0.76 | -0.71 | -56.0% | 2886 |
| vol_filtered_trend | ETH | -27.7% | -25.2% | -24.4% | 58 | 76 | 38% | -0.23% | 0.84 | -0.35 | -49.5% | 1472 |
| ma_trend | SOL | -38.6% | -45.5% | -39.5% | 62 | 108 | 29% | -0.28% | 0.84 | -0.35 | -66.9% | 2051 |
| breakout | SOL | -27.3% | -45.5% | -18.7% | 44 | 47 | 32% | -0.43% | 0.80 | -0.29 | -52.4% | 916 |
| rsi_reversion | SOL | -32.7% | -45.5% | -22.5% | 48 | 69 | 59% | -0.42% | 0.77 | -0.32 | -48.1% | 1124 |
| bollinger_reversion | SOL | -42.2% | -45.5% | -26.2% | 32 | 91 | 60% | -0.49% | 0.71 | -0.59 | -57.6% | 1435 |
| vol_filtered_trend | SOL | -13.3% | -45.5% | -28.7% | 72 | 68 | 37% | +0.03% | 0.93 | 0.02 | -44.6% | 1406 |


## 2. Overfitting check: in-sample vs. out-of-sample

Train window = what an optimiser would report. Walk-forward = what actually happened afterwards.

| strategy | coin | best params (train) | train net return | train expectancy | walk-forward expectancy |
|---|---|---|---|---|---|
| ma_trend | BTC | {"fast": 50, "slow": 100} | +146.6% | +2.18% | -0.08% |
| breakout | BTC | {"entry_n": 72, "exit_n": 72} | +115.5% | +3.69% | -0.06% |
| rsi_reversion | BTC | {"n": 14, "entry": 20, "exit": 60} | +16.3% | +1.40% | +0.43% |
| bollinger_reversion | BTC | {"n": 50, "k": 2.0} | -2.1% | +0.01% | -0.34% |
| vol_filtered_trend | BTC | {"fast": 50, "slow": 200, "q": 0.9} | +58.3% | +1.13% | -0.18% |
| ma_trend | ETH | {"fast": 10, "slow": 100} | +66.3% | +0.86% | -0.33% |
| breakout | ETH | {"entry_n": 336, "exit_n": 72} | +61.3% | +5.77% | +1.47% |
| rsi_reversion | ETH | {"n": 14, "entry": 20, "exit": 60} | -5.9% | -0.43% | -0.04% |
| bollinger_reversion | ETH | {"n": 20, "k": 2.0} | -12.2% | -0.04% | -0.26% |
| vol_filtered_trend | ETH | {"fast": 50, "slow": 200, "q": 0.9} | -8.7% | -0.01% | -0.23% |
| ma_trend | SOL | {"fast": 20, "slow": 50} | +349.9% | +2.11% | -0.28% |
| breakout | SOL | {"entry_n": 72, "exit_n": 24} | +221.1% | +3.23% | -0.43% |
| rsi_reversion | SOL | {"n": 14, "entry": 30, "exit": 60} | +71.0% | +1.46% | -0.42% |
| bollinger_reversion | SOL | {"n": 50, "k": 2.0} | +94.4% | +0.96% | -0.49% |
| vol_filtered_trend | SOL | {"fast": 50, "slow": 200, "q": 0.9} | +161.9% | +1.88% | +0.03% |


## 3. Stability across time (all parameter sets in the grid)

Median net return of the *whole grid* per period, and share of grid configs that were profitable. Strategies that only work in one regime show up here.

| strategy | coin | 2023-10..2024-09 | 2024-10..2025-09 | 2025-10..2026-02 |
|---|---|---|---|---|
| ma_trend | BTC | +59.6% (100% pos) vs B&H +133.9% | +2.1% (50% pos) vs B&H +79.0% | -26.0% (0% pos) vs B&H -41.6% |
| breakout | BTC | +17.4% (82% pos) vs B&H +133.9% | +15.5% (82% pos) vs B&H +79.0% | -14.6% (0% pos) vs B&H -41.6% |
| rsi_reversion | BTC | +4.9% (67% pos) vs B&H +133.9% | -1.9% (33% pos) vs B&H +79.0% | -17.4% (17% pos) vs B&H -41.6% |
| bollinger_reversion | BTC | -21.4% (0% pos) vs B&H +133.9% | -5.7% (0% pos) vs B&H +79.0% | -33.1% (0% pos) vs B&H -41.6% |
| vol_filtered_trend | BTC | -5.9% (33% pos) vs B&H +133.9% | -7.8% (33% pos) vs B&H +79.0% | -24.3% (0% pos) vs B&H -41.6% |
| ma_trend | ETH | +44.9% (100% pos) vs B&H +55.0% | -7.3% (38% pos) vs B&H +57.8% | -30.9% (0% pos) vs B&H -52.8% |
| breakout | ETH | +15.0% (82% pos) vs B&H +55.0% | +25.5% (73% pos) vs B&H +57.8% | -9.3% (9% pos) vs B&H -52.8% |
| rsi_reversion | ETH | -19.6% (0% pos) vs B&H +55.0% | -23.4% (0% pos) vs B&H +57.8% | -16.6% (17% pos) vs B&H -52.8% |
| bollinger_reversion | ETH | -18.1% (0% pos) vs B&H +55.0% | -29.2% (0% pos) vs B&H +57.8% | -23.3% (0% pos) vs B&H -52.8% |
| vol_filtered_trend | ETH | -17.6% (0% pos) vs B&H +55.0% | -30.3% (17% pos) vs B&H +57.8% | -18.7% (0% pos) vs B&H -52.8% |
| ma_trend | SOL | +261.5% (100% pos) vs B&H +612.8% | +7.0% (75% pos) vs B&H +35.0% | -41.7% (0% pos) vs B&H -59.5% |
| breakout | SOL | +155.1% (100% pos) vs B&H +612.8% | +5.8% (73% pos) vs B&H +35.0% | -26.6% (0% pos) vs B&H -59.5% |
| rsi_reversion | SOL | +10.4% (100% pos) vs B&H +612.8% | -22.8% (0% pos) vs B&H +35.0% | -11.4% (17% pos) vs B&H -59.5% |
| bollinger_reversion | SOL | +38.8% (100% pos) vs B&H +612.8% | -35.9% (0% pos) vs B&H +35.0% | -26.9% (0% pos) vs B&H -59.5% |
| vol_filtered_trend | SOL | +12.5% (67% pos) vs B&H +612.8% | -8.7% (33% pos) vs B&H +35.0% | -32.0% (0% pos) vs B&H -59.5% |


## 4. Lockbox (last 6 months, evaluated once)

Period 2026-03-01 to 2026-09-01. Parameters frozen from all pre-lockbox data.

### By strategy

| strategy | avg net return (3 coins) | avg buy&hold | coins profitable | avg expectancy/trade | total trades | avg beats-random % |
|---|---|---|---|---|---|---|
| ma_trend | +3.9% | +21.2% | 1/3 | +0.45% | 69 | 48 |
| breakout | +7.5% | +21.2% | 2/3 | +0.90% | 32 | 62 |
| rsi_reversion | -11.4% | +21.2% | 0/3 | -1.80% | 34 | 14 |
| bollinger_reversion | -15.3% | +21.2% | 0/3 | -0.51% | 87 | 21 |
| vol_filtered_trend | +5.4% | +21.2% | 3/3 | +0.30% | 81 | 57 |

### Every strategy x coin

| strategy | coin | net return | buy&hold | random (mean) | beats random % | trades | win rate | expectancy/trade | profit factor | Sharpe | max DD | fees paid $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ma_trend | BTC | -8.2% | +17.3% | +1.3% | 33 | 25 | 36% | -0.23% | 0.77 | -0.43 | -31.6% | 443 |
| breakout | BTC | +14.5% | +17.3% | +3.6% | 78 | 10 | 30% | +1.59% | 2.09 | 1.21 | -12.7% | 194 |
| rsi_reversion | BTC | -7.6% | +17.3% | +0.5% | 13 | 5 | 80% | -1.38% | 0.45 | -0.81 | -17.1% | 99 |
| bollinger_reversion | BTC | -18.4% | +17.3% | -4.8% | 12 | 36 | 61% | -0.51% | 0.49 | -1.55 | -25.8% | 628 |
| vol_filtered_trend | BTC | +3.1% | +17.3% | +0.5% | 60 | 29 | 41% | +0.14% | 1.12 | 0.36 | -14.8% | 582 |
| ma_trend | ETH | -5.9% | +25.4% | +7.5% | 26 | 26 | 31% | -0.04% | 0.86 | -0.10 | -36.6% | 427 |
| breakout | ETH | -6.0% | +25.4% | +0.1% | 28 | 10 | 30% | -0.38% | 0.74 | -0.47 | -23.0% | 175 |
| rsi_reversion | ETH | -14.5% | +25.4% | +1.0% | 6 | 4 | 50% | -3.62% | 0.18 | -1.34 | -21.1% | 77 |
| bollinger_reversion | ETH | -19.3% | +25.4% | -0.6% | 12 | 23 | 57% | -0.83% | 0.45 | -1.43 | -27.9% | 410 |
| vol_filtered_trend | ETH | +10.5% | +25.4% | +6.7% | 57 | 21 | 43% | +0.57% | 1.33 | 0.72 | -20.0% | 429 |
| ma_trend | SOL | +25.8% | +21.1% | +4.2% | 84 | 18 | 50% | +1.62% | 1.85 | 1.31 | -21.6% | 351 |
| breakout | SOL | +14.0% | +21.1% | +2.5% | 79 | 12 | 42% | +1.49% | 1.55 | 1.06 | -18.9% | 213 |
| rsi_reversion | SOL | -12.0% | +21.1% | -0.3% | 24 | 25 | 64% | -0.39% | 0.67 | -0.61 | -26.5% | 463 |
| bollinger_reversion | SOL | -8.1% | +21.1% | -1.2% | 38 | 28 | 75% | -0.18% | 0.79 | -0.43 | -28.0% | 522 |
| vol_filtered_trend | SOL | +2.7% | +21.1% | +1.8% | 54 | 31 | 45% | +0.20% | 1.05 | 0.33 | -26.5% | 577 |


## 5. Verdict

Evidence-of-edge test per strategy/coin cell: positive net return, positive expectancy per trade, and beating >=95% of random-entry runs.
- Walk-forward: **0 of 15** cells pass.
- Lockbox: **0 of 15** cells pass.

**No edge found.** On unseen data, after 0.30% round-trip costs, none of the five simple strategies
(MA trend, breakout, RSI reversion, Bollinger reversion, vol-filtered trend) on BTC, ETH or SOL hourly candles
showed a reliable positive expectancy.

- **Walk-forward (Oct 2024 to Feb 2026):** 13 of 15 strategy/coin cells lost money. The two winners (RSI on BTC, breakout on ETH)
  made +6.5% and +16% on only 18 and 19 trades and did not beat 95% of random-entry runs; with 15 cells tested, a couple of
  such results are expected by chance. Bollinger mean reversion was the worst (high win rate ~60%, but losses larger than wins and heavy fees),
  a clear example that win rate does not equal profit.
- **Lockbox (Mar to Aug 2026, one look):** 0 of 15 cells passed. The market rose (buy-and-hold +17% BTC, +25% ETH, +21% SOL) and
  almost every strategy trailed it. The best, MA trend on SOL (+25.8%), beat only 84% of random runs on 18 trades, and the same strategy
  lost money on BTC and ETH. Breakout won on BTC and SOL but lost on ETH, and it had been the one 'winner' in walk-forward on ETH.
  Results flip sign across coins and periods, which is what noise looks like.
- **Confidence:** moderate-to-high that these specific simple rules have no exploitable edge on this data after costs; low confidence
  that *nothing* works. Costs of 0.30% per round trip consume a large share of a typical hourly move (median |1h move| is 0.2-0.4%).
- **Main risks and limits:** only 5 strategies, tiny grids, long-only, hourly bars only (5m was downloaded and explored but not backtested; costs are even
  harder to beat there); 35 months is a single market cycle; trade counts per cell are small (5-110), so individual cells are statistically weak;
  slippage is a flat 0.05% assumption, not a measured one; no funding/borrowing, taxes or partial fills.
- **Bottom line:** no justification for live or testnet trading on the basis of this evidence. Any next step should be a new,
  pre-registered hypothesis (for example a different timeframe, cross-sectional or market-neutral ideas), not more tuning of these rules,
  because the lockbox has now been used.

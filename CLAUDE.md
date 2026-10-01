# Crypto Research Lab — project rules

This is a research and learning project. Its job is to find out, honestly, whether a
trading strategy has an edge on Binance spot data. It is not a money-making bot yet.

## Hard rules
- Phase 1 uses public historical data only. No API keys, no account access, no orders.
- Never place real orders. A later phase may use the Binance Spot **Testnet** only, and only
  after the owner explicitly approves that phase in chat.
- Never store secrets in code or commit them. If keys are ever needed (testnet), read them
  from a `.env` file that is git-ignored.
- Every backtest must include fees (default 0.10% per side) and slippage (default 0.05% per
  side). Results without costs are not reported as results.
- Never tune parameters on the final hold-out ("lockbox") period. It is evaluated once.
- Report results honestly. If nothing beats the baselines after costs, say so plainly.
  "No edge found" is a valid and useful outcome.

## Engineering
- Python 3.11+, virtual env in `.venv`, dependencies pinned in `requirements.txt`.
- Data in `data/` (git-ignored), stored as Parquet.
- Keep strategy logic free of look-ahead: a signal on bar `t` can only trade at bar `t+1`'s open.
- Add focused `pytest` tests for the backtest engine (fees, position accounting, no look-ahead).

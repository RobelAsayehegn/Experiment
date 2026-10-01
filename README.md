# Crypto Research Lab

Research project: does any simple trading strategy have a real edge on Binance spot data
**after fees and slippage**? "No edge found" is a valid result.

**Phase 1 only:** public historical data (data.binance.vision), backtesting, no API keys,
no account access, no orders. See `CLAUDE.md` for the project rules and `START_PROMPT.md`
for the milestone plan.

## Setup (Windows)

```powershell
uv venv --python 3.12 .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
pytest
```

`requirements.in` lists the direct dependencies; `requirements.txt` is the pinned freeze.

## Layout

| Path | Purpose |
|---|---|
| `src/data/` | Downloader, checksum verification, Parquet merge, quality checks |
| `src/backtest/` | Backtest engine (fees, slippage, next-bar execution) and metrics |
| `src/strategies/` | One file per strategy hypothesis, plus baselines |
| `src/reports/` | Exploration charts and final report generation |
| `tests/` | pytest tests for the engine (fees, accounting, no look-ahead) |
| `data/` | Downloaded + merged data (git-ignored) |
| `reports/` | Generated charts and reports |

## Cost defaults

Fee 0.10% per side, slippage 0.05% per side. Results without costs are not reported.

## Validation plan

Training period, walk-forward validation, and a final 6-month lockbox evaluated exactly once.

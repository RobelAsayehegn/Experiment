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

## Running the pipeline

```powershell
python -m src.data.download                       # 5m, 1h, 4h klines (add --intervals 4h for one)
python -m src.data.quality                        # gaps / duplicates / bad candles
python -m src.reports.explore                     # exploration charts -> reports/
python -m src.reports.run_validation --interval 1h   # walk-forward, all long & long/short variants
python -m src.reports.run_validation --interval 4h
python -m src.reports.build_dashboard             # -> dashboard/data.js
```

Open `dashboard/index.html` (double-click) or serve it: `python -m http.server 8765 --directory dashboard`.

## Long/short note

Binance spot cannot short. Short legs are simulated like a perpetual future on the same price
series: same fee and slippage, plus a holding cost (default 0.01% per 8h). Real funding and
liquidation risk are not modelled.

## Lockbox status

The last 6 months (2026-03-01 .. 2026-08-31) were evaluated once, for the original 1h long-only
strategies (`reports/lockbox_results.json`, guard in `src/reports/run_lockbox.py`). That period is
spent: the 4h and long/short variants get walk-forward results only, and need data published after
2026-08-31 for their own one-shot lockbox.

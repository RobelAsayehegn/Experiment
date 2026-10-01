"""Data-quality checks on the merged Parquet files: gaps, duplicates, bad prices.

Usage:  python -m src.data.quality
"""
from __future__ import annotations

import pandas as pd

from .download import INTERVALS, PARQUET_DIR, RAW_DIR, SYMBOLS, read_zip

STEP = {"5m": pd.Timedelta(minutes=5), "1h": pd.Timedelta(hours=1)}


def load(symbol: str, interval: str) -> pd.DataFrame:
    return pd.read_parquet(PARQUET_DIR / f"{symbol}_{interval}.parquet")


def check(symbol: str, interval: str) -> dict:
    step = STEP[interval]
    raw = pd.concat([read_zip(f) for f in sorted((RAW_DIR / symbol / interval).glob("*.zip"))])
    raw_dupes = int(raw["open_time"].duplicated().sum())

    df = load(symbol, interval)
    t = df["open_time"]
    diffs = t.diff().dropna()
    gaps = diffs[diffs > step]
    missing = int(((gaps / step) - 1).sum())
    bad = int(
        ((df[["open", "high", "low", "close"]] <= 0).any(axis=1)
         | (df["high"] < df["low"])
         | (df["high"] < df[["open", "close"]].max(axis=1))
         | (df["low"] > df[["open", "close"]].min(axis=1))).sum()
    )
    expected = int((t.iloc[-1] - t.iloc[0]) / step) + 1
    gap_list = [(str(t[i - 1]), int(g / step) - 1) for i, g in zip(gaps.index, gaps)]
    return {
        "symbol": symbol, "interval": interval, "rows": len(df),
        "start": str(t.iloc[0]), "end": str(t.iloc[-1]),
        "expected_rows": expected, "missing_candles": missing,
        "duplicates_in_raw": raw_dupes, "invalid_ohlc_rows": bad,
        "zero_volume_rows": int((df["volume"] == 0).sum()),
        "gaps": gap_list,
    }


def main() -> None:
    rows = []
    for s in SYMBOLS:
        for i in INTERVALS:
            rows.append(check(s, i))
    summary = pd.DataFrame(rows).drop(columns="gaps")
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(summary.to_string(index=False))
    for r in rows:
        if r["gaps"]:
            shown = r["gaps"][:8]
            more = f" (+{len(r['gaps']) - 8} more)" if len(r["gaps"]) > 8 else ""
            print(f"\n{r['symbol']} {r['interval']} gaps [after_candle, n_missing]: {shown}{more}")


if __name__ == "__main__":
    main()

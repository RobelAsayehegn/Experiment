"""Download monthly klines from data.binance.vision, verify SHA256, merge to Parquet.

Public data only: no API keys, no account access.

Usage:  python -m src.data.download [--months 36]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVALS = ["5m", "1h", "4h"]
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PARQUET_DIR = ROOT / "data" / "parquet"

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]


def month_range(n_months: int, today: date | None = None) -> list[str]:
    """Last `n_months` fully completed months as 'YYYY-MM', oldest first."""
    today = today or date.today()
    y, m = today.year, today.month
    months = []
    for _ in range(n_months):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        months.append(f"{y}-{m:02d}")
    return months[::-1]


def _file_name(symbol: str, interval: str, month: str) -> str:
    return f"{symbol}-{interval}-{month}.zip"


def _url(symbol: str, interval: str, month: str) -> str:
    return f"{BASE_URL}/{symbol}/{interval}/{_file_name(symbol, interval, month)}"


def download_month(symbol: str, interval: str, month: str, session: requests.Session) -> tuple[str, str]:
    """Download one zip and verify it against its .CHECKSUM. Returns (name, status)."""
    name = _file_name(symbol, interval, month)
    dest = RAW_DIR / symbol / interval / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = _url(symbol, interval, month)

    r = session.get(url + ".CHECKSUM", timeout=60)
    if r.status_code == 404:
        return name, "missing (404)"
    r.raise_for_status()
    expected = r.text.split()[0].lower()

    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected:
        return name, "cached"

    for attempt in range(3):
        resp = session.get(url, timeout=120)
        resp.raise_for_status()
        if hashlib.sha256(resp.content).hexdigest() == expected:
            dest.write_bytes(resp.content)
            return name, "ok"
    raise RuntimeError(f"Checksum mismatch after 3 attempts: {name}")


def read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    first = raw[:20]
    header = 0 if not first[:1].isdigit() else None  # some files carry a header row
    df = pd.read_csv(io.BytesIO(raw), header=header, names=COLUMNS if header is None else None)
    df.columns = COLUMNS
    # Binance switched spot timestamps to microseconds in 2025; normalise to ms.
    for c in ("open_time", "close_time"):
        df[c] = df[c].where(df[c] < 10**14, df[c] // 1000)
    return df


def merge_to_parquet(symbol: str, interval: str) -> Path:
    files = sorted((RAW_DIR / symbol / interval).glob("*.zip"))
    df = pd.concat([read_zip(f) for f in files], ignore_index=True)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.drop(columns="ignore")
    for c in ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"):
        df[c] = df[c].astype("float64")
    df["trades"] = df["trades"].astype("int64")
    # Duplicates are reported by quality.py on the raw merge; keep the first here.
    df = df.sort_values("open_time").drop_duplicates("open_time", keep="first").reset_index(drop=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    out = PARQUET_DIR / f"{symbol}_{interval}.parquet"
    df.to_parquet(out, index=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=36)
    ap.add_argument("--intervals", nargs="+", default=INTERVALS)
    args = ap.parse_args()

    months = month_range(args.months)
    jobs = [(s, i, m) for s in SYMBOLS for i in args.intervals for m in months]
    print(f"{len(jobs)} files: {months[0]} .. {months[-1]}")

    session = requests.Session()
    done = 0
    problems = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(download_month, s, i, m, session): (s, i, m) for s, i, m in jobs}
        for f in as_completed(futs):
            done += 1
            try:
                name, status = f.result()
            except Exception as e:  # noqa: BLE001
                problems.append((futs[f], repr(e)))
                continue
            if status.startswith("missing"):
                problems.append((futs[f], status))
            if done % 20 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    if problems:
        print("Problems:")
        for p in problems:
            print("  ", p)

    for s in SYMBOLS:
        for i in args.intervals:
            print("merged ->", merge_to_parquet(s, i))


if __name__ == "__main__":
    main()

"""Build dashboard/data.js (and copy charts) from reports/results/*.json.

Open dashboard/index.html in a browser; it needs no server and no internet.

Usage:  python -m src.reports.build_dashboard
"""
from __future__ import annotations

import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.strategies.registry import DESCRIPTIONS

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "reports" / "results"
DASH = ROOT / "dashboard"


def clean(o):
    """JSON-safe: NaN/inf -> None."""
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def main() -> None:
    DASH.mkdir(exist_ok=True)
    data = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "descriptions": DESCRIPTIONS, "intervals": {}, "meta": {}, "lockbox": None}
    for iv in ("1h", "4h"):
        f = RESULTS / f"validation_{iv}.json"
        if f.exists():
            j = json.loads(f.read_text())
            data["intervals"][iv] = j["coins"]
            data["meta"][iv] = j["meta"]

    lb = ROOT / "reports" / "lockbox_results.json"   # written once by run_lockbox (1h, long-only variants)
    if lb.exists():
        j = json.loads(lb.read_text())
        lock = {"period": [j["period_start"][:10], j["period_end"][:10]], "interval": "1h", "cells": {}}
        for key, r in j["results"].items():
            strat, sym = key.split("|")
            lock["cells"].setdefault(sym, {})[strat] = {
                "metrics": r["metrics"], "buy_hold": r["buy_hold"]["net_return"],
                "random": r["random"], "percentile_vs_random": r["percentile_vs_random"], "params": r["params"]}
        data["lockbox"] = lock

    (DASH / "img").mkdir(exist_ok=True)
    imgs = []
    for p in sorted((ROOT / "reports").glob("*.png")):
        shutil.copy(p, DASH / "img" / p.name)
        imgs.append(p.name)
    data["images"] = imgs
    (DASH / "data.js").write_text("window.DATA = " + json.dumps(clean(data)) + ";\n", encoding="utf-8")
    print(f"wrote dashboard/data.js ({(DASH / 'data.js').stat().st_size / 1024:.0f} KB); intervals: {list(data['intervals'])}")


if __name__ == "__main__":
    main()

"""Report test results: console summary + result.json."""
from __future__ import annotations
import json
import time
from pathlib import Path
from tests.base import PASS, FAIL, SKIP, ERROR


def report(results, meta: dict, out_dir: Path, log=print) -> bool:
    counts = {PASS: 0, FAIL: 0, SKIP: 0, ERROR: 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    overall = (counts[FAIL] == 0 and counts[ERROR] == 0)

    # ---- console -----------------------------------------------------------
    log("")
    log("=" * 60)
    log(" AUTO-UT RESULTS")
    for k, v in meta.items():
        log(f"   {k}: {v}")
    log("-" * 60)
    for r in results:
        log(f"   [{r.status:5}] {r.name:22} {r.seconds:6.1f}s  {_first_line(r.detail)}")
    log("-" * 60)
    log(f"   PASS={counts[PASS]}  FAIL={counts[FAIL]}  "
        f"ERROR={counts[ERROR]}  SKIP={counts[SKIP]}   "
        f"=> {'OVERALL PASS' if overall else 'OVERALL FAIL'}")
    log("=" * 60)

    # ---- JSON --------------------------------------------------------------
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall": "PASS" if overall else "FAIL",
        "counts": counts,
        "meta": meta,
        "results": [r.to_dict() for r in results],
    }
    stamp = time.strftime("%Y%m%d_%H%M%S")
    latest = out_dir / "result.json"
    archived = out_dir / f"result_{stamp}.json"
    for f in (latest, archived):
        f.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"   JSON -> {latest}  (and {archived.name})")
    return overall


def _first_line(s):
    return (s or "").splitlines()[0][:80] if s else ""

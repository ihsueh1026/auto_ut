"""Run a list of Test objects in order, collecting TestResults.

If a `critical` test fails/errors, the remaining tests are marked SKIP (the
device is not in a state where they could meaningfully run - e.g. it didn't
boot). Non-critical failures do not stop the run.
"""
from __future__ import annotations
from tests.base import Test, PASS


def run_tests(tests, device, log=print):
    results = []
    blocked = None            # name of the critical test that blocked the rest
    for t in tests:
        if blocked:
            results.append(Test.skipped(t.name, f"skipped: {blocked} failed"))
            log(f"  [SKIP] {t.name}  (blocked by {blocked})")
            continue

        log(f"  [RUN ] {t.name} ...")
        r = t.run(device)
        results.append(r)
        log(f"  [{r.status:4}] {t.name}  ({r.seconds}s)  {_first_line(r.detail)}")

        if r.status != PASS and getattr(t, "critical", False):
            blocked = t.name
            log(f"  !! critical test '{t.name}' did not pass - skipping the rest")
    return results


def _first_line(s):
    return (s or "").splitlines()[0] if s else ""

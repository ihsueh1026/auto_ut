"""Test interface. Each test = one file with a subclass of Test.

Contract: implement check(device) -> (bool ok, str detail). The base times it,
catches exceptions, and returns a TestResult. Set critical=True for tests that
gate the rest (e.g. boot health - if it fails, later tests can't run).
"""
from __future__ import annotations
import time
import traceback
from dataclasses import dataclass, field, asdict


PASS, FAIL, SKIP, ERROR = "PASS", "FAIL", "SKIP", "ERROR"


@dataclass
class TestResult:
    name: str
    status: str          # PASS / FAIL / SKIP / ERROR
    detail: str = ""
    seconds: float = 0.0

    def to_dict(self):
        return asdict(self)


class Test:
    name = "unnamed"
    critical = False     # if True and it fails, remaining tests are SKIPped

    def check(self, device):
        """Override. Return (ok: bool, detail: str)."""
        raise NotImplementedError

    def run(self, device) -> TestResult:
        t0 = time.time()
        try:
            ok, detail = self.check(device)
            status = PASS if ok else FAIL
        except Exception:
            status, detail = ERROR, "exception:\n" + traceback.format_exc()
        return TestResult(self.name, status, detail, round(time.time() - t0, 1))

    @staticmethod
    def skipped(name, reason) -> TestResult:
        return TestResult(name, SKIP, reason, 0.0)

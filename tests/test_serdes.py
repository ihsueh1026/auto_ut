"""SerDes / LSLink functional test (mirrors the SerDes test-item list).

One case, non-critical (boot_health already gates "device usable"):

  Platform_SerDes.GZI3 - SerDes is alive AND the LSLink CLI round-trips:
    * i2c "ping" node reads "ok"
    * switch golden -> flashid main/sub (LS) + main-hs/sub-hs (HS)
      -> switch feature -> version main/sub == 0x13

The lslink_cli binary name is config.LSLINK_CLI ("lslink_cli" on PATH by
default); pass a different one if it lives at e.g. /data/lslink_cli. The ping
node is config.SERDES_PING_NODE.
"""
from __future__ import annotations
from tests.base import Test


def _snip(s, n=160):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + "..."


class SerDesTest(Test):
    """Run the SerDes alive check + the lslink_cli sequence, checking each
    step's expected output.

    Each step is (label, shell-command, required-substrings, timeout). A step
    passes when the command returns 0 and every required substring
    (case-insensitive) is present. Substrings are chosen to be
    spacing-independent (part numbers / version literal), so they survive minor
    CLI formatting changes. W25Q32JW = LS (4 MiB, ef6016); W25Q128JW = HS
    (16 MiB, ef6018); Feature version = 0x13.
    """
    name = "Platform_SerDes.GZI3"
    critical = False

    def __init__(self, cli="lslink_cli", ping_node="/sys/bus/i2c/devices/9-0020/ping"):
        self.cli = cli
        self.ping_node = ping_node

    def _steps(self):
        c = self.cli
        return [
            # (label, shell command, required substrings (lowercased), timeout)
            ("serdes alive (ping)", "cat " + self.ping_node, ("ok",),      15),
            ("switch golden",       c + " switch golden",     ("golden", "ok"),  90),
            ("flashid main",        c + " flashid main",      ("w25q32jw",),     30),
            ("flashid sub",         c + " flashid sub",       ("w25q32jw",),     30),
            ("flashid main-hs",     c + " flashid main-hs",   ("w25q128jw",),    30),
            ("flashid sub-hs",      c + " flashid sub-hs",    ("w25q128jw",),    30),
            ("switch feature",      c + " switch feature",    ("feature", "ok"), 90),
            ("version main",        c + " version main",      ("0x13",),         30),
            ("version sub",         c + " version sub",       ("0x13",),         30),
        ]

    def check(self, device):
        device.root()          # best-effort; the ping sysfs node is root-only

        steps = self._steps()
        passed, fails = 0, []
        for label, cmd, needles, timeout in steps:
            rc, out = device.shell(cmd, timeout=timeout)
            lo = out.lower()
            missing = [n for n in needles if n not in lo]
            if rc == 0 and not missing:
                passed += 1
                continue
            why = f"rc={rc}" if rc != 0 else "missing " + "+".join(missing)
            fails.append(f"[{label}] {why} | out='{_snip(out)}'")

        total = len(steps)
        if fails:
            return False, f"{passed}/{total} steps OK; FAIL: " + " ;; ".join(fails)
        return True, f"{total}/{total} steps OK (ping/golden/flashid LS+HS/feature/version 0x13)"

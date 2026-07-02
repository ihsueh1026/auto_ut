"""Boot health check - the first, critical test after flashing.

Dev-stage builds don't always set sys.boot_completed, so the ONLY hard gate is
that the device comes back as an adb `device`. sys.boot_completed, fingerprint,
and the crash log are collected as best-effort notes (they never fail the test).
"""
from __future__ import annotations
from tests.base import Test


class BootHealthTest(Test):
    name = "boot_health"
    critical = True

    def __init__(self, boot_timeout_s=300):
        self.boot_timeout_s = boot_timeout_s

    def check(self, device):
        # HARD gate: device shows up on adb ----------------------------------
        if not device.wait_adb(self.boot_timeout_s):
            return False, (f"no adb device within {self.boot_timeout_s}s "
                           f"(adb state={device.adb_state()}) - didn't boot / not enumerated?")

        notes = ["adb=device"]

        # best-effort: boot_completed (dev builds may never set it) ----------
        bc = device.getprop("sys.boot_completed")
        notes.append(f"boot_completed={bc or '-'}")

        # best-effort: build identity (also confirms shell responds) ---------
        fp = device.getprop("ro.build.fingerprint")
        if fp:
            notes.append(f"fingerprint={fp}")

        # best-effort: no fresh crash in the crash buffer --------------------
        crash = device.crash_log()
        bad = [l for l in crash.splitlines()
               if any(k in l for k in ("beginning of crash", "FATAL EXCEPTION",
                                       "Kernel panic", "has crashed"))]
        if bad:
            notes.append("WARN crash-log: " + bad[0][:160])

        # best-effort: no kernel panic / oops / call-trace in dmesg ----------
        # try adb root first (works on userdebug/eng; refused on production).
        rooted = device.root()
        notes.append("root" if rooted else "no-root")
        dmesg = device.dmesg()
        if not dmesg:
            notes.append("dmesg=n/a")     # no root / restricted on this build
        else:
            KERN = ("Kernel panic", "Unable to handle kernel", "Call trace:",
                    "kernel BUG", "BUG:", "Oops", "Internal error",
                    "Synchronous External Abort", "watchdog")
            hits = [l for l in dmesg.splitlines()
                    if any(k in l for k in KERN)]
            if hits:
                notes.append(f"WARN dmesg({len(hits)}): " + hits[0].strip()[:160])
            else:
                notes.append("dmesg=clean")

        return True, "; ".join(notes)

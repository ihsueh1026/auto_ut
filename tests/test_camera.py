"""Camera module test - mirrors the Optical_Camera list.

  Optical_Camera.GZI3.001  camera module test
    adb root; adb remount; adb reboot
    (after reboot) adb root; adb remount
    mkdir /vendor/etc/camera/
    echo enableNCSService=FALSE >> /vendor/etc/camera/camxoverridesettings.txt
    stop vendor.camera-provider
    nativehaltest --gtest_filter=CameraModuleTest.TestNumberOfCamera
    -> expect gtest "[1 PASSED] and [0 FAILED]"

Fully automated but heavy: it needs root + remount (writable /vendor) and
REBOOTS the device once to apply the remount, then applies the camera override
and runs the gtest. Pass = at least 1 PASSED and 0 FAILED.
"""
from __future__ import annotations
import re

import config
from tests.base import Test


def _snip(s, n=200):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + "..."


class CameraTest(Test):
    name = "Optical_Camera.GZI3"
    critical = False

    def __init__(self, boot_timeout_s=300):
        self.boot_timeout_s = boot_timeout_s

    def check(self, device):
        # phase 1: root + remount, then reboot to apply the remount ------------
        device.root()
        rc, out = device.adb("remount", timeout=90)
        device.log(f"[camera] remount(1): {_snip(out, 80)}")

        device.log("[camera] rebooting to apply remount ...")
        device.adb("reboot", timeout=30)
        if not device.wait_adb(self.boot_timeout_s):
            return False, (f"device did not come back within {self.boot_timeout_s}s "
                           f"after reboot (state={device.adb_state()})")

        # phase 2: root + remount again, apply override, stop provider ----------
        device.root()
        rc, out = device.adb("remount", timeout=90)
        device.log(f"[camera] remount(2): {_snip(out, 80)}")

        device.shell(f"mkdir -p {config.CAMERA_OVERRIDE_DIR}")
        device.shell(f"echo {config.CAMERA_OVERRIDE_LINE} >> {config.CAMERA_OVERRIDE_FILE}")
        device.shell(f"stop {config.CAMERA_PROVIDER}")

        # run the gtest -------------------------------------------------------
        rc, out = device.shell(config.CAMERA_GTEST, timeout=120)

        # nativetest format: "[1 PASSED] and [0 FAILED]"
        m = re.search(r'\[(\d+)\s*PASSED\]\s*and\s*\[(\d+)\s*FAILED\]', out, re.I)
        if m:
            passed, failed = int(m.group(1)), int(m.group(2))
            ok = passed >= 1 and failed == 0
            detail = f"gtest: {passed} passed, {failed} failed"
            return ok, detail if ok else detail + f" | {_snip(out)}"

        # fallback: standard gtest summary lines
        pas = re.search(r'\[\s*PASSED\s*\]\s*(\d+)', out)
        failed_line = re.search(r'\[\s*FAILED\s*\]', out)
        if pas and not failed_line:
            return True, f"gtest PASSED {pas.group(1)} (standard format)"

        return False, f"no PASS/FAIL summary in gtest output (rc={rc}) | {_snip(out)}"

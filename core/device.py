"""Thin adb/fastboot wrapper for one device + boot/health waiting helpers.

All adb/fastboot calls use stdin=DEVNULL so a long-running child (e.g. adb shell)
can never swallow the caller's stdin.
"""
from __future__ import annotations
import subprocess
import time


class Device:
    def __init__(self, serial=None, adb="adb", fastboot="fastboot", log=print):
        self.serial = serial
        self.adb_bin = adb
        self.fastboot_bin = fastboot
        self.log = log

    # ---- low level ----------------------------------------------------------
    def _sel(self, tool):
        return [tool] + (["-s", self.serial] if self.serial else [])

    def _run(self, argv, timeout):
        try:
            p = subprocess.run(argv, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=timeout)
            return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
        except subprocess.TimeoutExpired:
            return 124, "[timeout]"
        except FileNotFoundError:
            return 127, f"[not found: {argv[0]}]"

    def adb(self, *args, timeout=60):
        return self._run(self._sel(self.adb_bin) + list(args), timeout)

    def fastboot(self, *args, timeout=300):
        return self._run(self._sel(self.fastboot_bin) + list(args), timeout)

    def shell(self, cmd, timeout=60):
        return self.adb("shell", cmd, timeout=timeout)

    def getprop(self, name, timeout=15):
        rc, out = self.shell("getprop " + name, timeout=timeout)
        return out if rc == 0 else ""

    # ---- state --------------------------------------------------------------
    def adb_state(self):
        rc, out = self.adb("get-state", timeout=10)
        return out if rc == 0 else "absent"

    def in_fastboot(self):
        rc, out = self.fastboot("devices", timeout=10)
        if rc != 0:
            return False
        lines = [l for l in out.splitlines() if l.strip()]
        if self.serial:
            return any(self.serial in l for l in lines)
        return len(lines) > 0

    # ---- transitions --------------------------------------------------------
    def reboot_bootloader(self):
        self.log("[device] adb reboot bootloader")
        return self.adb("reboot", "bootloader", timeout=30)

    def fastboot_reboot(self):
        self.log("[device] fastboot reboot")
        return self.fastboot("reboot", timeout=60)

    # ---- waits (all bounded) ------------------------------------------------
    def wait_fastboot(self, timeout, poll=2):
        end = time.time() + timeout
        while time.time() < end:
            if self.in_fastboot():
                return True
            time.sleep(poll)
        return self.in_fastboot()

    def wait_adb(self, timeout, poll=3):
        end = time.time() + timeout
        while time.time() < end:
            if self.adb_state() == "device":
                return True
            time.sleep(poll)
        return self.adb_state() == "device"

    def wait_boot_completed(self, timeout, poll=3):
        """adb device appears AND sys.boot_completed==1 within `timeout`."""
        end = time.time() + timeout
        if not self.wait_adb(timeout=timeout):
            return False
        while time.time() < end:
            if self.getprop("sys.boot_completed") == "1":
                return True
            time.sleep(poll)
        return self.getprop("sys.boot_completed") == "1"

    # ---- health helpers -----------------------------------------------------
    def crash_log(self):
        """Best-effort recent crash buffer (no root needed). '' if none/unavailable."""
        rc, out = self.adb("logcat", "-b", "crash", "-d", "-t", "200", timeout=20)
        return out if rc == 0 else ""

    def root(self, timeout=30):
        """Try to restart adbd as root (userdebug/eng only). Returns True if root
        is available. On production builds adbd refuses and this returns False.
        adbd restarts on success, so we wait for the device to reconnect."""
        rc, out = self.adb("root", timeout=timeout)
        lo = out.lower()
        if "cannot run as root" in lo or "production" in lo or rc == 127:
            return False
        self.wait_adb(timeout=timeout)          # adbd bounced; wait for reconnect
        who = self.getprop("service.adb.root")  # 1 when adbd is root
        if who == "1":
            return True
        rc2, uid = self.shell("id -u", timeout=10)
        return rc2 == 0 and uid.strip() == "0"

    def dmesg(self, timeout=20):
        """Best-effort kernel ring buffer. May need root on some builds; returns
        '' if unavailable / permission denied."""
        rc, out = self.shell("dmesg", timeout=timeout)
        if rc != 0 or not out or "permission denied" in out.lower():
            return ""
        return out

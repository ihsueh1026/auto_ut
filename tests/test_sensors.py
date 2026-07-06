"""Sensor functional test (mirrors the Platform_Sensor test-item list).

One case, non-critical, running the SSC "see" tool checks in order:

  002 IMU_Whoami accel      ssc_sensor_info -sensor=accel | grep NAME  -> lsm6dsv
  003 IMU_Accel_Streaming   see_workhorse -sensor=accel ...            -> ACCURACY_HIGH
  004 IMU_Accel_SelfTest    see_selftest -sensor=accel -testtype=hw    -> test_type HW x2 + test_passed 1
  005 IMU_Gyro_SelfTest     see_selftest -sensor=gyro -testtype=hw     -> "
  006 IMU_Gyro_Streaming    see_workhorse -sensor=gyro ...             -> ACCURACY_HIGH
  007 Mag_whoami            ssc_sensor_info -sensor=mag | grep NAME    -> bmm350
  008 Mag_Streaming         see_workhorse -sensor=mag ...              -> ACCURACY_HIGH
  009 Mag_SelfTest          see_selftest -sensor=mag -testtype=hw      -> test_type HW x2 + test_passed 1
  010 ALS_Whoami            cat .../input*/name | head -1              -> tsl2522
  011 ALS_lux               getevent -lt | grep ABS_MISC              -> >=1 numeric ABS_MISC in 5-10s

Self-test writes a result json under config.SENSOR_JSON_DIR; on pass we remove
it (per the spec), on fail we keep it for debug. ALS lux captures input events
for a few seconds and passes if at least one ABS_MISC (the ALS lux report)
arrives with a numeric value. Most steps need root (sysfs / /data/vendor), so
adb root is attempted first.
"""
from __future__ import annotations
import re

import config
from tests.base import Test


def _snip(s, n=140):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + "..."


class SensorTest(Test):
    name = "Platform_Sensor.GZI3"
    critical = False

    def __init__(self, json_dir=None):
        self.json_dir = json_dir or config.SENSOR_JSON_DIR

    # ---- individual checks: each returns (label, ok, detail) ----------------
    def _whoami(self, device, sensor, expect):
        rc, out = device.shell(
            f'ssc_sensor_info -sensor={sensor} | grep NAME', timeout=20)
        ok = rc == 0 and expect.lower() in out.lower()
        return (f"{sensor} whoami", ok, f"want {expect}; got '{_snip(out, 60)}'")

    def _streaming(self, device, sensor):
        rc, out = device.shell(
            f'see_workhorse -sensor={sensor} -display_events=1 -duration=5',
            timeout=40)
        ok = rc == 0 and config.SENSOR_STREAM_STATUS.lower() in out.lower()
        detail = "ACCURACY_HIGH events" if ok else f"no HIGH-accuracy events; '{_snip(out)}'"
        return (f"{sensor} streaming", ok, detail)

    def _selftest(self, device, sensor):
        jf = f"{self.json_dir}/{config.SENSOR_SELFTEST_JSON[sensor]}"
        device.shell(f"rm -f {jf}", timeout=15)                 # fresh result
        device.shell(f"see_selftest -sensor={sensor} -testtype=hw", timeout=40)

        _, types = device.shell(f"cat {jf} | grep test_type", timeout=15)
        _, passed = device.shell(f"cat {jf} | grep test_pass", timeout=15)

        n_hw = len(re.findall(re.escape(config.SENSOR_SELFTEST_TYPE), types, re.I))
        pass_ok = re.search(r'test_passed"?\s*:\s*1\b', passed) is not None
        ok = n_hw >= 2 and pass_ok

        if ok:
            device.shell(f"rm -f {jf}", timeout=15)             # spec: drop on pass
        detail = (f"test_type HW x{n_hw} (need >=2), test_passed={'1' if pass_ok else '!1'}"
                  + ("" if ok else f" [kept {jf}]"))
        return (f"{sensor} selftest", ok, detail)

    def _als_whoami(self, device):
        rc, out = device.shell(
            f'cat {config.ALS_INPUT_DIR}/input*/name | head -n 1', timeout=15)
        ok = rc == 0 and config.ALS_WHOAMI.lower() in out.lower()
        return ("als whoami", ok, f"want {config.ALS_WHOAMI}; got '{_snip(out, 60)}'")

    def _als_lux(self, device):
        # capture input events for a window; the ALS reports lux as ABS_MISC.
        # PASS if >=1 ABS_MISC arrives within ALS_CAPTURE_S and its value is numeric.
        out = device.capture_shell("getevent -lt", config.ALS_CAPTURE_S)
        hits = [ln.strip() for ln in out.splitlines() if config.ALS_LUX_EVENT in ln]

        value = None
        for ln in hits:
            # getevent -l prints the value as the last token (hex, e.g. 000001a3)
            m = re.search(config.ALS_LUX_EVENT + r'\s+([0-9a-fx]+)\b', ln, re.I)
            if m:
                try:
                    int(m.group(1), 16)      # numeric (hex) value?
                    value = m.group(1)
                    break
                except ValueError:
                    continue

        w = config.ALS_CAPTURE_S
        if value is not None:
            return ("als lux", True,
                    f"{config.ALS_LUX_EVENT} received within {w}s "
                    f"({len(hits)} events, value={value})")
        if hits:
            return ("als lux", False,
                    f"{config.ALS_LUX_EVENT} seen but value not numeric: {_snip(hits[0])}")
        return ("als lux", False, f"no {config.ALS_LUX_EVENT} within {w}s")

    # ---- run all, aggregate --------------------------------------------------
    def check(self, device):
        rooted = device.root()          # sysfs writes + /data/vendor need root
        results = [("root", True, "root" if rooted else "no-root (steps may fail)")]

        results.append(self._whoami(device, "accel", config.SENSOR_WHOAMI["accel"]))
        results.append(self._streaming(device, "accel"))
        results.append(self._selftest(device, "accel"))
        results.append(self._selftest(device, "gyro"))
        results.append(self._streaming(device, "gyro"))
        results.append(self._whoami(device, "mag", config.SENSOR_WHOAMI["mag"]))
        results.append(self._streaming(device, "mag"))
        results.append(self._selftest(device, "mag"))
        results.append(self._als_whoami(device))
        results.append(self._als_lux(device))

        # the leading "root" note never fails the test
        checks = results[1:]
        passed = sum(1 for _, ok, _ in checks if ok)
        total = len(checks)
        fails = [f"[{lbl}] {det}" for lbl, ok, det in checks if not ok]

        head = f"{passed}/{total} checks OK ({results[0][2]})"
        if fails:
            return False, head + "; FAIL: " + " ;; ".join(fails)
        return True, head

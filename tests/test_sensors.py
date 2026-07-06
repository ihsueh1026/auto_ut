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
  011 ALS_lux               enable ALS, read data/lux + data/valid     -> valid=1 + numeric lux

Self-test writes a result json under config.SENSOR_JSON_DIR; on pass we remove
it (per the spec), on fail we keep it for debug. ALS lux is INTERACTIVE on a
terminal: it prompts you to cover (dark) then light (bright) the sensor and
checks valid==1 plus dark lux < bright lux. With no tty (mail-triggered) it
falls back to auto-checking valid==1 + a numeric lux (dark/bright comparison
skipped). Most steps need root (sysfs writes / /data/vendor), so adb root is
attempted first.
"""
from __future__ import annotations
import re
import sys

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

    def _als_find_node(self, device):
        """Return the ALS input node path (name == ALS_NODE_NAME), or ''."""
        d, nm = config.ALS_INPUT_DIR, config.ALS_NODE_NAME
        cmd = (f'for p in {d}/input*; do n=$(cat "$p/name" 2>/dev/null); '
               f'if [ "$n" = "{nm}" ]; then echo "$p"; break; fi; done')
        _, out = device.shell(cmd, timeout=15)
        out = out.strip()
        return out.splitlines()[-1].strip() if out else ""

    def _als_read(self, device, node):
        """Read (lux:int|None, valid:str) from an enabled ALS node."""
        _, out = device.shell(
            f'echo "lux=$(cat "{node}/data/lux" 2>/dev/null)"; '
            f'echo "valid=$(cat "{node}/data/valid" 2>/dev/null)"', timeout=15)
        mlux = re.search(r'lux=(-?\d+)', out)
        mval = re.search(r'valid=(\d+)', out)
        return (int(mlux.group(1)) if mlux else None,
                mval.group(1) if mval else "?")

    def _als_lux(self, device):
        node = self._als_find_node(device)
        if not node:
            return ("als lux", False,
                    f"ALS node (name={config.ALS_NODE_NAME}) not found under "
                    f"{config.ALS_INPUT_DIR}")

        device.shell(f'echo 1 > "{node}/config/enable"', timeout=10)
        try:
            if sys.stdin.isatty():
                # interactive: compare a dark reading vs a bright reading.
                print(f"\n>>> [als] 請【遮住】ALS 感測器（暗環境）。")
                input(">>> [als] 遮好後按 Enter…")
                device.shell("sleep 1")
                dark, vdark = self._als_read(device, node)
                print(f">>> [als] 暗：lux={dark} valid={vdark}")

                print(f">>> [als] 請【照亮】ALS 感測器（亮環境）。")
                input(">>> [als] 照好後按 Enter…")
                device.shell("sleep 1")
                bright, vbright = self._als_read(device, node)
                print(f">>> [als] 亮：lux={bright} valid={vbright}")

                valid_ok = vdark == "1" and vbright == "1"
                got = dark is not None and bright is not None
                cmp_ok = got and dark < bright
                ok = valid_ok and cmp_ok
                detail = (f"dark lux={dark}(valid={vdark}), bright lux={bright}"
                          f"(valid={vbright}); dark<bright={cmp_ok}")
                return ("als lux", ok, detail)

            # non-interactive: no light control -> auto-check valid=1 + numeric lux.
            device.shell("sleep 1")
            lux, valid = self._als_read(device, node)
            ok = valid == "1" and lux is not None
            detail = (f"valid={valid}, lux={lux} "
                      f"(NOTE: dark<bright comparison skipped - non-interactive)")
            return ("als lux", ok, detail)
        finally:
            device.shell(f'echo 0 > "{node}/config/enable"', timeout=10)

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

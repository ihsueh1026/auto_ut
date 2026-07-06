#!/usr/bin/env python3
"""Auto-UT: download a build, flash the device, verify it boots, run tests.

Flow:  download(UNC .zip -> image dir)  ->  flash (adb reboot bootloader ->
flash_all.bat -> fastboot reboot)  ->  boot health (critical)  ->  more tests
->  report (console + result.json).

Both download and flash are swappable (Downloader / Flasher ABCs). Run on
Windows with adb/fastboot on PATH and a single device attached.

Examples:
  python autotest.py                         # use config.BUILD_ZIP
  python autotest.py --build \\\\host\\path\\build.zip
  python autotest.py --local-dir D:\\imgs\\GZI3   # already-unzipped build
  python autotest.py --skip-flash            # just run tests on current device
  python autotest.py --serial 1234abcd --force
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import config
from core.device import Device
from core.downloader import UncZipDownloader, LocalDirDownloader
from core.flasher import FastbootBatFlasher, FlashError
from core.runner import run_tests
from core.reporter import report
from tests.base import TestResult, FAIL, ERROR
from tests.test_boot_health import BootHealthTest
from tests.test_serdes import SerDesTest
from tests.test_sensors import SensorTest
from tests.test_keys import KeyTest


class Tee:
    """print to console and append to a run log file."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(path, "a", encoding="utf-8")

    def __call__(self, *args):
        line = " ".join(str(a) for a in args)
        ts = time.strftime("%H:%M:%S")
        print(line)
        self.fh.write(f"{ts} {line}\n")
        self.fh.flush()


# Test registry: (canonical key, {aliases}, factory(args)). Order = run order.
# Boot health runs first and is critical (if it fails the device isn't usable,
# so the rest are SKIPped). `--tests` selects a subset by key/alias/case-id.
TEST_REGISTRY = [
    ("boot", {"boot", "boot_health"},
     lambda a: BootHealthTest(boot_timeout_s=a.boot_timeout)),
    ("serdes", {"serdes", "lslink", "platform_serdes.gzi3"},
     lambda a: SerDesTest(cli=config.LSLINK_CLI, ping_node=config.SERDES_PING_NODE)),
    ("sensors", {"sensors", "sensor", "platform_sensor.gzi3"},
     lambda a: SensorTest(json_dir=config.SENSOR_JSON_DIR)),
    ("key", {"key", "keypad", "platform_keypad.gzi3"},
     lambda a: KeyTest()),
]


def test_keys():
    """Human-readable list of selectable keys for --help / the mail prompt."""
    return ", ".join(k for k, _, _ in TEST_REGISTRY)


def build_tests(args):
    """The plug-in point for adding tests. Returns the tests to run, honoring
    --tests (comma list of keys/aliases/case-ids; 'all' or empty = everything),
    always in registry order. Add a Test subclass by extending TEST_REGISTRY."""
    sel = (getattr(args, "tests", "") or "all").strip().lower()
    if sel in ("", "all", "*"):
        return [factory(args) for _, _, factory in TEST_REGISTRY]

    wanted = {t.strip() for t in sel.split(",") if t.strip()}
    chosen, matched = [], set()
    for key, aliases, factory in TEST_REGISTRY:
        if wanted & ({key} | aliases):
            chosen.append(factory(args))
            matched |= wanted & ({key} | aliases)
    unknown = wanted - matched
    if unknown:
        raise SystemExit(f"[error] unknown --tests: {', '.join(sorted(unknown))}. "
                         f"Available: {test_keys()} (or 'all').")
    return chosen


def parse_args(argv):
    p = argparse.ArgumentParser(description="Auto download-flash-test for SW6100.")
    p.add_argument("--build", default=config.BUILD_ZIP,
                   help="build source: a .zip OR a directory (auto-picks the newest "
                        ".zip). Default: config.BUILD_ZIP")
    p.add_argument("--ask", action="store_true",
                   help="prompt to type/paste the build path at runtime")
    p.add_argument("--local-dir",
                   help="use an already-unzipped image dir instead of --build")
    p.add_argument("--work", default=str(config.WORK_DIR),
                   help=f"working dir (default: {config.WORK_DIR})")
    p.add_argument("--serial", help="adb/fastboot device serial (single device: omit)")
    p.add_argument("--skip-download", action="store_true",
                   help="reuse the already-downloaded/extracted build in --work")
    p.add_argument("--skip-flash", action="store_true",
                   help="skip download+flash; just run tests on the current device")
    p.add_argument("--tests", default="all",
                   help="which tests to run: comma list of keys/aliases/case-ids "
                        "(e.g. 'boot,002' or '001'); 'all' = everything. "
                        f"Available: {test_keys()}")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="echo each adb shell command and its output live during tests")
    p.add_argument("--force", action="store_true",
                   help="force re-copy and re-unzip even if cached")
    p.add_argument("--boot-timeout", type=int, default=config.BOOT_TIMEOUT_S)
    p.add_argument("--fastboot-wait", type=int, default=config.FASTBOOT_WAIT_S)
    p.add_argument("--flash-timeout", type=int, default=config.FLASH_TIMEOUT_S)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])

    # let the user type/paste the build path (filename changes every build)
    if args.ask and not args.local_dir:
        entered = input(f"build path (dir or .zip) [{args.build}]: ").strip().strip('"')
        if entered:
            args.build = entered

    work = Path(args.work)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log = Tee(work / "logs" / f"autotest_{stamp}.log")

    log("=" * 60)
    log(" AUTO-UT start")
    log(f"   build      = {args.build}")
    log(f"   local-dir  = {args.local_dir}")
    log(f"   work       = {work}")
    log(f"   serial     = {args.serial or '(single device)'}")
    log(f"   skip-flash = {args.skip_flash}")
    log(f"   tests      = {args.tests}")
    log(f"   verbose    = {args.verbose}")
    log("=" * 60)

    device = Device(serial=args.serial, adb=config.ADB, fastboot=config.FASTBOOT,
                    log=log, verbose=args.verbose)
    meta = {"build": args.build if not args.local_dir else args.local_dir,
            "serial": args.serial or "single", "skip_flash": args.skip_flash,
            "tests": args.tests}

    # resolve the test selection up front so a bad --tests fails before flashing
    tests = build_tests(args)
    log(f"[tests] selected: {', '.join(t.name for t in tests)}")

    results = []

    # ---- download + flash (unless --skip-flash) ----------------------------
    if not args.skip_flash:
        try:
            if args.skip_download and not args.local_dir:
                dl = LocalDirDownloader(work / "images", config.IMAGE_MARKER, log=log)
            elif args.local_dir:
                dl = LocalDirDownloader(args.local_dir, config.IMAGE_MARKER, log=log)
            else:
                dl = UncZipDownloader(args.build, work, config.IMAGE_MARKER,
                                      force=args.force, log=log)
            image_dir = dl.fetch()

            flasher = FastbootBatFlasher(
                config.FLASH_BAT, fastboot_wait_s=args.fastboot_wait,
                flash_timeout_s=args.flash_timeout, log_dir=work / "logs", log=log)
            t0 = time.time()
            flasher.flash(image_dir, device)
            results.append(TestResult("flash", "PASS",
                           f"flashed {image_dir}", round(time.time() - t0, 1)))
        except (FlashError, FileNotFoundError, OSError) as e:
            log(f"[FATAL] download/flash failed: {e}")
            results.append(TestResult("flash", FAIL, f"{type(e).__name__}: {e}", 0.0))
            ok = report(results, meta, work / "results", log=log)
            return 0 if ok else 1
        except Exception as e:  # noqa: BLE001 - unexpected, keep it in the report
            log(f"[FATAL] unexpected download/flash error: {e}")
            results.append(TestResult("flash", ERROR, f"{type(e).__name__}: {e}", 0.0))
            report(results, meta, work / "results", log=log)
            return 1
    else:
        log("[flash] --skip-flash: running tests on the current device")

    # ---- tests -------------------------------------------------------------
    log("")
    log("[tests] running ...")
    results += run_tests(tests, device, log=log)

    # ---- report ------------------------------------------------------------
    ok = report(results, meta, work / "results", log=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

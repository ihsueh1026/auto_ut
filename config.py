"""Auto-UT configuration (defaults; most are overridable on the CLI)."""
import os
from pathlib import Path

# --- Build source: the exact build .zip to download & flash. The weekly folder
#     and filename change every build, so update this (or pass --build / --ask)
#     each time. A directory is also accepted but you must then point at a folder
#     that contains exactly one .zip - otherwise specify the full .zip path. -----
BUILD_ZIP = (
    r"\\sdrdfs1\AK7\GZI3\2_WeeklyFormal_Build\CMBUILD"
    r"\GZI3.0068.PR1.2606291.F_000150\GZI3.0068.PR1.2606291.F.zip"
)

# --- Local working area (downloads / extracted images / logs / results). Anchor
#     it to THIS file's folder so it lands in auto_ut\_ut_work no matter what the
#     current working dir is (Outlook / cmd launch it with a different CWD). -----
WORK_DIR = Path(__file__).resolve().with_name("_ut_work")

# --- Flashing (current method = fastboot). Windows uses flash_all.bat; Linux/
#     macOS uses flash_all.sh (the vendor XML-driven flasher). Picked by OS. -----
_HERE = Path(__file__).resolve().parent
FLASH_SCRIPT = _HERE / ("flash_all.bat" if os.name == "nt" else "flash_all.sh")
FLASH_BAT = FLASH_SCRIPT   # back-compat alias
# A distinctive image that only exists in the fastboot image dir; used to locate
# the image dir inside the unzipped build tree.
IMAGE_MARKER = "super.img"

# --- Tools (assumed on PATH; override if needed) -------------------------------
ADB = "adb"
FASTBOOT = "fastboot"

# --- SerDes / LSLink tests -----------------------------------------------------
# lslink_cli as invoked over `adb shell` (on PATH here; use "/data/lslink_cli"
# if it was pushed there instead).
LSLINK_CLI = "lslink_cli"
SERDES_PING_NODE = "/sys/bus/i2c/devices/9-0020/ping"

# --- Sensor tests (Qualcomm SSC "see" tools) -----------------------------------
SENSOR_JSON_DIR = "/data/vendor/sensors"        # where see_selftest drops results
# whoami: `ssc_sensor_info -sensor=<s> | grep NAME` must report this chip.
SENSOR_WHOAMI = {"accel": "lsm6dsv", "mag": "bmm350"}
# streaming (`see_workhorse`) events must carry this sample status.
SENSOR_STREAM_STATUS = "SNS_STD_SENSOR_SAMPLE_STATUS_ACCURACY_HIGH"
# self-test (`see_selftest -testtype=hw`) result json per sensor + expected type.
SENSOR_SELFTEST_JSON = {
    "accel": "accel_STMicro_see_salt.json",
    "gyro":  "gyro_STMicro_see_salt.json",
    "mag":   "mag_Bosch_see_salt.json",
}
SENSOR_SELFTEST_TYPE = "SNS_PHYSICAL_SENSOR_TEST_TYPE_HW"
# ALS (ambient light): i2c input dir, expected whoami name, and the node `name`
# used to locate the iio/input node that exposes config/enable + data/lux|valid.
ALS_INPUT_DIR = "/sys/bus/i2c/devices/9-0039/input"
ALS_WHOAMI = "tsl2522"
ALS_NODE_NAME = "als"

# --- Key / keypad test (interactive; someone must press the button) ------------
# getevent prints `<node>: <type> <code> <value>`; POWER = EV_KEY(0001) KEY_POWER
# (0074) with value 00000001 (down) / 00000000 (up).
KEY_EV_TYPE = "0001"
KEY_POWER_CODE = "0074"
KEY_CAPTURE_S = 8              # seconds to capture getevent while you press

# --- Camera test (nativehaltest gtest; needs root + remount, reboots once) -----
CAMERA_OVERRIDE_DIR = "/vendor/etc/camera"
CAMERA_OVERRIDE_FILE = "/vendor/etc/camera/camxoverridesettings.txt"
CAMERA_OVERRIDE_LINE = "enableNCSService=FALSE"
CAMERA_PROVIDER = "vendor.camera-provider"
CAMERA_GTEST = "nativehaltest --gtest_filter=CameraModuleTest.TestNumberOfCamera"

# --- Timeouts (seconds) --------------------------------------------------------
FASTBOOT_WAIT_S = 90       # after `adb reboot bootloader`, wait for fastboot
FLASH_TIMEOUT_S = 1800     # flash_all.bat whole run
BOOT_TIMEOUT_S = 300       # after fastboot reboot, wait for sys.boot_completed

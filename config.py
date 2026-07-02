"""Auto-UT configuration (defaults; most are overridable on the CLI)."""
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

# --- Flashing (current method = fastboot via flash_all.bat) --------------------
FLASH_BAT = Path(__file__).resolve().with_name("flash_all.bat")
# A distinctive image that only exists in the fastboot image dir; used to locate
# the image dir inside the unzipped build tree.
IMAGE_MARKER = "super.img"

# --- Tools (assumed on PATH; override if needed) -------------------------------
ADB = "adb"
FASTBOOT = "fastboot"

# --- Timeouts (seconds) --------------------------------------------------------
FASTBOOT_WAIT_S = 90       # after `adb reboot bootloader`, wait for fastboot
FLASH_TIMEOUT_S = 1800     # flash_all.bat whole run
BOOT_TIMEOUT_S = 300       # after fastboot reboot, wait for sys.boot_completed

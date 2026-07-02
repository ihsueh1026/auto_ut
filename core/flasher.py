"""Flash a build onto the device.

Flasher is the extension point: to change flashing method later (EDL / QFIL /
python fastboot), add a subclass; the main flow only calls .flash(image_dir).
"""
from __future__ import annotations
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path


class FlashError(Exception):
    pass


class Flasher(ABC):
    @abstractmethod
    def flash(self, image_dir: Path, device) -> None:
        """Flash the images in image_dir and leave the device rebooting.
        Raise FlashError on failure."""
        raise NotImplementedError


class FastbootBatFlasher(Flasher):
    """Enter fastboot via `adb reboot bootloader`, run the flash script from the
    image dir, then `fastboot reboot`.

    Picks the runner by the script's extension: `.bat` -> Windows shell; anything
    else (`.sh`) -> bash. Failure is detected from BOTH the exit code (the vendor
    flash_all.sh exits non-zero on a failed flash) and error strings in the output
    (flash_all.bat continues past a failure, so its output must be scanned)."""

    def __init__(self, flash_bat: Path, fastboot_wait_s=90, flash_timeout_s=1800,
                 log_dir: Path = None, log=print):
        self.flash_bat = Path(flash_bat)
        self.fastboot_wait_s = fastboot_wait_s
        self.flash_timeout_s = flash_timeout_s
        self.log_dir = Path(log_dir) if log_dir else None
        self.log = log

    def flash(self, image_dir: Path, device) -> None:
        if not self.flash_bat.exists():
            raise FlashError(f"flash script not found: {self.flash_bat}")
        image_dir = Path(image_dir)

        # 1) get into fastboot -------------------------------------------------
        if device.in_fastboot():
            self.log("[flash] already in fastboot")
        else:
            device.reboot_bootloader()
            self.log(f"[flash] waiting up to {self.fastboot_wait_s}s for fastboot ...")
            if not device.wait_fastboot(self.fastboot_wait_s):
                raise FlashError("device did not enter fastboot mode")
        self.log("[flash] fastboot device present")

        # 2) run the flash script with cwd = image dir (its paths are relative)
        self.log(f"[flash] running {self.flash_bat.name} in {image_dir}")
        rc, out = self._run_script(image_dir)
        self._save_log(out)
        lo = out.lower()
        if rc != 0 or "FAILED" in out or "error:" in lo or "flash failed" in lo:
            raise FlashError(f"flash script reported failure (rc={rc}) - see flash log")

        # 3) reboot into the OS (the flash script does not reboot itself) -----
        rc, rout = device.fastboot_reboot()
        if rc != 0:
            raise FlashError(f"fastboot reboot failed: {rout}")
        self.log("[flash] flashing done, device rebooting")

    def _run_script(self, image_dir: Path):
        """Returns (returncode, combined_output)."""
        if self.flash_bat.suffix.lower() == ".bat":
            argv, use_shell = [str(self.flash_bat)], True   # Windows: cmd runs .bat
        else:
            argv, use_shell = ["bash", str(self.flash_bat)], False   # .sh via bash
        try:
            p = subprocess.run(
                argv, cwd=str(image_dir),
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                shell=use_shell, timeout=self.flash_timeout_s)
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired as e:
            raise FlashError(f"flash timed out after {self.flash_timeout_s}s") from e

    def _save_log(self, text: str):
        if not self.log_dir:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        f = self.log_dir / f"flash_{time.strftime('%Y%m%d_%H%M%S')}.log"
        f.write_text(text, encoding="utf-8", errors="replace")
        self.log(f"[flash] log -> {f}")

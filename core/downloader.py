"""Fetch a build and hand back the fastboot image directory.

Downloader is the extension point: add HTTP / scp subclasses later; the main
flow only calls .fetch() -> Path(image_dir).
"""
from __future__ import annotations
import shutil
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path


class Downloader(ABC):
    @abstractmethod
    def fetch(self) -> Path:
        """Make the build available locally; return the dir that holds the
        fastboot images (the dir flash_all.bat must run in)."""
        raise NotImplementedError


class UncZipDownloader(Downloader):
    """Copy a build .zip from a Windows UNC share, unzip it, locate the image dir.

    The source may be a specific .zip OR a directory - handy because the weekly
    build folder/filename changes every time. When it's a directory the newest
    *.zip found (this level or one below) is picked automatically.
    """

    def __init__(self, src, work_dir: Path, marker="super.img", force=False, log=print):
        self.src = str(src)
        self.work_dir = Path(work_dir)
        self.marker = marker
        self.force = force
        self.log = log

    def _resolve_zip(self) -> Path:
        p = Path(self.src)
        if p.suffix.lower() == ".zip":
            return p
        if p.is_dir():
            # only auto-use a dir when it unambiguously holds ONE .zip; never
            # guess among many (a build folder has target_files/etc. too).
            zips = list(p.glob("*.zip"))
            if len(zips) == 1:
                self.log(f"[download] using the only .zip in {p}: {zips[0].name}")
                return zips[0]
            if not zips:
                raise FileNotFoundError(f"no .zip in {p} - give the full .zip path")
            names = ", ".join(sorted(f.name for f in zips))
            raise FileNotFoundError(
                f"{len(zips)} zips in {p} ({names}); specify the exact .zip "
                f"(config.BUILD_ZIP / --build / --ask)")
        raise FileNotFoundError(f"build source is neither a .zip nor a directory: {p}")

    def fetch(self) -> Path:
        src = self._resolve_zip()
        name = src.name
        dl_dir = self.work_dir / "downloads"
        ex_dir = self.work_dir / "images" / src.stem
        dl_dir.mkdir(parents=True, exist_ok=True)
        local_zip = dl_dir / name

        # 1) copy from UNC (skip if cached with matching size) --------------
        self._copy(src, local_zip)

        # 2) unzip (skip if already extracted, unless --force) --------------
        marker_hits = list(ex_dir.rglob(self.marker)) if ex_dir.exists() else []
        if self.force or not marker_hits:
            if ex_dir.exists():
                self.log(f"[download] wiping stale {ex_dir}")
                shutil.rmtree(ex_dir, ignore_errors=True)
            ex_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"[download] unzipping -> {ex_dir}")
            with zipfile.ZipFile(local_zip) as z:
                z.extractall(ex_dir)
        else:
            self.log(f"[download] already extracted at {ex_dir}")

        # 3) locate the image dir (the dir containing the marker image) -----
        hits = list(ex_dir.rglob(self.marker))
        if not hits:
            raise FileNotFoundError(
                f"marker '{self.marker}' not found under {ex_dir} - "
                f"is this a fastboot build zip?")
        image_dir = hits[0].parent
        self.log(f"[download] image dir = {image_dir}")
        return image_dir

    def _copy(self, src: Path, dst: Path):
        try:
            ssz = src.stat().st_size
        except OSError as e:
            raise FileNotFoundError(f"cannot access build zip {src}: {e}")
        if not self.force and dst.exists() and dst.stat().st_size == ssz:
            self.log(f"[download] cached {dst} ({ssz/1e6:.0f} MB) - skip copy")
            return
        self.log(f"[download] copying {src} -> {dst} ({ssz/1e6:.0f} MB) ...")
        shutil.copy2(src, dst)
        self.log("[download] copy done")


class LocalDirDownloader(Downloader):
    """Build is already an unzipped image dir (or a dir containing one) locally."""

    def __init__(self, path, marker="super.img", log=print):
        self.path = Path(path)
        self.marker = marker
        self.log = log

    def fetch(self) -> Path:
        hits = [self.path / self.marker]
        if not hits[0].exists():
            hits = list(self.path.rglob(self.marker))
        if not hits:
            raise FileNotFoundError(f"marker '{self.marker}' not found under {self.path}")
        self.log(f"[download] image dir = {hits[0].parent}")
        return hits[0].parent

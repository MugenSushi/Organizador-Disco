"""Organizador de Disco — organiza unidades extraibles con medios (videos, juegos, ROMs)."""

# SECTION 1 — stdlib imports (zero external dependencies)
import ctypes
import json
import logging
import os
import re
import shutil
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# SECTION 2 — Constants

# Ground truth: Ordenar.ps1 $NO_TOUCH_EXTS — full superset.
# Note: REQUIREMENTS.md INFRA-03 omits .cso, .pbp, .v64; Ordenar.ps1 is authoritative (CONTEXT.md).
NO_TOUCH_EXTS: frozenset[str] = frozenset({
    ".iso", ".bin", ".cue", ".img", ".mdf", ".nrg", ".chd", ".cso", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".n64", ".z64", ".v64",
    ".3ds", ".cia", ".nds", ".gcm", ".wbfs", ".wad", ".xci", ".nsp",
})

# All lowercase — matched via path.lower() for case-insensitive Windows paths.
# Ground truth: Ordenar.ps1 $SKIP_PATH_PARTS
SKIP_PATH_PARTS: tuple[str, ...] = (
    "\\system volume information\\",
    "\\$recycle.bin\\",
    "\\windowsapps\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\amazon games\\",
)

LOG_DIR_NAME = "_organizer_logs"
DRIVE_REMOVABLE = 2  # GetDriveTypeW constant for removable media

# SECTION 3 — Module-level logger (before all function/class definitions)
logger = logging.getLogger("organizer")


# SECTION 4 — Drive detection helpers

def get_removable_drives() -> list[dict]:
    """Return list of dicts: [{root, label, size_gb, serial}] for all removable drives."""
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    drives = []
    for i in range(26):
        if not (bitmask & (1 << i)):
            continue
        letter = chr(ord("A") + i)
        root = letter + ":\\"
        if kernel32.GetDriveTypeW(root) != DRIVE_REMOVABLE:
            continue
        label = _get_volume_label(kernel32, root)
        size_gb = _get_drive_size_gb(kernel32, root)
        serial = _get_volume_serial(kernel32, root)
        drives.append({"root": root, "label": label, "size_gb": size_gb, "serial": serial})
    return drives


def _get_volume_label(kernel32, root: str) -> str:
    # Pitfall 1: NEVER pass None for a buffer Windows writes to — use create_unicode_buffer
    buf = ctypes.create_unicode_buffer(261)
    kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0)
    # Pitfall 2: unlabelled drive returns empty string — fallback to drive letter
    return buf.value or root.rstrip("\\")


def _get_volume_serial(kernel32, root: str) -> int:
    serial = ctypes.c_ulong()
    kernel32.GetVolumeInformationW(root, None, 0, ctypes.byref(serial), None, None, None, 0)
    return serial.value


def _get_drive_size_gb(kernel32, root: str) -> float:
    total = ctypes.c_ulonglong(0)
    kernel32.GetDiskFreeSpaceExW(root, None, ctypes.byref(total), None)
    return round(total.value / 1_073_741_824, 0)


# SECTION 5 — Safety helpers

def is_no_touch(path: str) -> bool:
    """True if the file extension is in the ROM/ISO hard-block list (INFRA-03)."""
    lower = path.lower()
    dot = lower.rfind(".")
    return lower[dot:] in NO_TOUCH_EXTS if dot >= 0 else False


def should_skip_path(path: str) -> bool:
    """True if the path contains any protected system folder component (INFRA-04)."""
    lower = path.lower()
    return any(part in lower for part in SKIP_PATH_PARTS)


# SECTION 6 — _free_path helper

def _free_path(dst: Path) -> Path:
    """Return dst unchanged if it does not exist; otherwise dst with (2), (3)... appended to stem."""
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# SECTION 7 — Executor class

class Executor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run  # mutable — Phase 2 menu: executor.dry_run = True

    def move(self, src: Path, dst: Path) -> Path | None:
        """Move src to collision-safe dst. Returns final path or None if blocked/errored."""
        src_str = str(src)
        # Hard blocks enforced at the single mutation point, never at call sites (INFRA-03, INFRA-04)
        if is_no_touch(src_str):
            logger.warning("SKIP (no-touch ext): %s", src)
            return None
        if should_skip_path(src_str):
            logger.warning("SKIP (protected path): %s", src)
            return None
        final_dst = _free_path(dst)
        if self.dry_run:
            logger.info("DRY-RUN MOVE: %s -> %s", src, final_dst)
            return final_dst
        self.ensure_dir(final_dst.parent)
        try:
            shutil.move(str(src), str(final_dst))  # NOT Path.rename — fails cross-filesystem
            logger.info("MOVE: %s -> %s", src, final_dst)
        except PermissionError:
            logger.error("DENY: %s (acceso denegado)", src)
            return None
        except OSError as exc:
            logger.error("ERR: %s : %s", src, exc)
            return None
        return final_dst

    def ensure_dir(self, path: Path) -> None:
        """Create directory tree. No-op in dry_run mode."""
        if self.dry_run:
            return
        path.mkdir(parents=True, exist_ok=True)

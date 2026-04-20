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

# Phase 2 constants — video organizer
VIDEO_EXTS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".mpg", ".mpeg", ".ts",
})

SUB_EXTS: tuple[str, ...] = (".srt", ".ass", ".sub", ".idx")

# Ground truth: Ordenar.ps1 lines 172-192. PC and Steam absent per D-04 (locked decision).
CONSOLE_SYSTEMS: tuple[str, ...] = ("PS1", "PS2", "PSP", "GBA", "GBC")

# Lowercase — compared via .lower(). Confirmed in 02-UI-SPEC.md (Claude's discretion).
SCAN_EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "_organizer_logs", "series", "peliculas", "juegos",
})

CLEANUP_EXCLUDE_NAMES: frozenset[str] = frozenset({
    "_organizer_logs",
})

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


# SECTION 8 — Two-stage logging setup

def setup_console_logging() -> logging.Logger:
    """Stage 1: call at startup before drive is known. Console output only."""
    logger = logging.getLogger("organizer")
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger


def add_file_logging(logger: logging.Logger, log_dir: Path) -> None:
    """Stage 2: call after drive is selected. Adds rotating file handler (INFRA-08)."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Pitfall 4: read-only media — fall back gracefully, do not crash
        logger.warning("No se pudo crear el directorio de logs (disco de solo lectura). Usando solo consola.")
        return
    log_file = log_dir / "organizer.log"
    fh = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2 MB per CLAUDE.md
        backupCount=3,              # 3 backups per CLAUDE.md
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)


def select_drive(drives: list[dict]) -> dict:
    """Select removable drive. Implements decisions D-01, D-02, D-03 (locked)."""
    # D-02: no drives found — print error and exit (no retry loop, no manual fallback)
    if not drives:
        print("No se encontraron unidades extraibles. Conecta un disco e intentalo de nuevo.")
        sys.exit(1)

    # D-01: exactly one drive — auto-select silently, no confirmation needed
    if len(drives) == 1:
        d = drives[0]
        print(f"Usando {d['root']} ({d['label']})")
        return d

    # D-03: multiple drives — numbered list: letter + label + size
    print("Unidades extraibles disponibles:")
    for i, d in enumerate(drives, 1):
        size_str = f"{int(d['size_gb'])} GB"
        print(f"  {i}) {d['root']} {d['label']} ({size_str})")

    while True:
        choice = input(f"Selecciona una unidad [1-{len(drives)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(drives):
            return drives[int(choice) - 1]
        print(f"Entrada invalida. Escribe un numero entre 1 y {len(drives)}.")


# SECTION 9 — Compiled regex patterns (Phase 2)
# Ground truth: Ordenar.ps1 line 236 (series) and line 278 (movies).
# Compiled at module level — never inside a function or loop (CLAUDE.md convention).

RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)

RE_MOVIE = re.compile(
    r"^(?P<title>.+?)\s\((?P<year>(?:19|20)\d{2})\)",
    re.IGNORECASE,
)


# SECTION 14 — Main menu loop and entry point

def show_menu(executor: Executor, drive: dict) -> None:
    """Numbered main menu (MENU-01). Phase 2-4 options shown as stubs for forward compatibility."""
    while True:
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar videos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir ultima operacion")
        print("  4) Detectar incoherencias")
        print("  0) Salir")
        choice = input("Opcion: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("(Disponible en Fase 2)")
        elif choice == "2":
            print("(Disponible en Fase 2)")
        elif choice == "3":
            print("(Disponible en Fase 3)")
        elif choice == "4":
            print("(Disponible en Fase 4)")
        else:
            print("Opcion invalida.")


def main() -> None:
    """Script entry point. No CLI arguments required (MENU-01)."""
    logger = setup_console_logging()
    drive = select_drive(get_removable_drives())

    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)

    executor = Executor(dry_run=False)
    show_menu(executor, drive)


if __name__ == "__main__":
    main()

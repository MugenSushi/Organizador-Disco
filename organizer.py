"""Organizador de Disco — organiza unidades extraibles con medios (videos, juegos, ROMs)."""

# SECTION 1 — stdlib imports (zero external dependencies)
import ctypes
import csv
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
    while counter <= 9999:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
    # Fallback: use timestamp suffix to guarantee uniqueness
    import time as _time
    ts = int(_time.time() * 1000)
    return parent / f"{stem} ({ts}){suffix}"


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


# SECTION 10 — TSV rename applier (RENAME-01, RENAME-02)

def apply_renames(executor, drive_root: Path) -> dict:
    """Apply renames from rename_plan.tsv. Returns summary counter dict."""
    plan_file = drive_root / "_organizer_logs" / "rename_plan.tsv"
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}

    if not plan_file.exists():
        print(f"No se encontro rename_plan.tsv en {drive_root}. "
              "Coloca el archivo en _organizer_logs\\ y vuelve a intentarlo.")
        return counts

    with open(plan_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    if not rows:
        print("El archivo rename_plan.tsv esta vacio.")
        return counts

    for i, row in enumerate(rows, 1):
        old_str = (row.get("old_path") or "").strip()
        new_str = (row.get("new_path") or "").strip()

        if not old_str or not new_str:
            logger.warning("Fila %d ignorada: faltan columnas old_path / new_path.", i)
            continue

        counts["procesados"] += 1
        src_raw = Path(old_str)  # literal — Path() never glob-expands (RENAME-02)
        dst_raw = Path(new_str)
        # Anchor relative paths to drive_root — TSV may use either absolute or relative forms.
        # A relative path resolved against CWD (the script dir) would silently miss all files.
        src = src_raw if src_raw.is_absolute() else drive_root / src_raw
        dst = dst_raw if dst_raw.is_absolute() else drive_root / dst_raw

        if not src.exists():
            logger.warning("SKIP (no existe): %s", src)
            counts["saltados"] += 1
            continue

        # GAP-2 fix: enforce drive_root containment — reject paths outside the drive.
        # Use string prefix comparison (Python 3.6+ compatible) instead of
        # Path.is_relative_to() which requires Python 3.9+.
        try:
            src_resolved = src.resolve()
            dst_resolved = dst.resolve()
        except OSError:
            logger.warning("Fila %d ignorada: no se pudo resolver la ruta.", i)
            counts["saltados"] += 1
            continue
        drive_root_str = str(drive_root.resolve()).lower()
        src_str_low = str(src_resolved).lower()
        dst_str_low = str(dst_resolved).lower()
        if not (src_str_low.startswith(drive_root_str + "\\") or src_str_low == drive_root_str) or \
                not (dst_str_low.startswith(drive_root_str + "\\") or dst_str_low == drive_root_str):
            logger.warning(
                "SKIP (path traversal): fila %d — ruta fuera de la unidad seleccionada: src=%s dst=%s",
                i, src_resolved, dst_resolved,
            )
            counts["saltados"] += 1
            continue
        result = executor.move(src, dst)
        if result is not None:
            counts["movidos"] += 1
        else:
            counts["errores"] += 1

    return counts


# SECTION 11 — Recursive video scanner (INFRA-05: os.scandir, never glob/rglob)

def _scan_videos_recursive(root: Path, exclude_roots: frozenset) -> list:
    """Return all video files under root, skipping excluded top-level dirs.

    Uses os.scandir exclusively (INFRA-05 — handles bracket chars in filenames).
    exclude_roots: lowercased folder names to skip when current dir is root.
    """
    results = []
    _walk(root, root, exclude_roots, results)
    return results


def _walk(drive_root: Path, start: Path, exclude_roots: frozenset, acc: list) -> None:
    """Iterative directory traversal — avoids recursion depth limit on deep structures."""
    stack = [start]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        if current == drive_root and entry.name.lower() in exclude_roots:
                            continue
                        if should_skip_path(entry.path):
                            continue
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        p = Path(entry.path)
                        if p.suffix.lower() in VIDEO_EXTS:
                            acc.append(p)
        except PermissionError:
            logger.warning("SKIP (permiso denegado): %s", current)


# SECTION 12 — Empty directory cleanup (ORG-05)

def _remove_empty_dirs(root: Path, counts_removed: list) -> None:
    """Remove empty directories under root (bottom-up). Never removes root itself.

    Uses Path.rmdir() (wraps os.rmdir) — only succeeds on empty dirs.
    shutil.rmtree is forbidden by ORG-05 requirement.
    Iterative implementation — avoids recursion depth limit on deep structures.
    """
    # Collect candidate dirs bottom-up using os.walk topdown=False.
    # os.walk handles its own internal iteration — no recursion depth concern.
    candidates = []
    for dirpath, dirnames, _ in os.walk(root, topdown=False, onerror=None):
        dir_path = Path(dirpath)
        if dir_path == root:
            continue  # never remove root itself
        if dir_path.name.lower() in CLEANUP_EXCLUDE_NAMES:
            continue
        candidates.append(dir_path)

    for child in candidates:
        try:
            child.rmdir()  # OSError if not empty — safe contract
            counts_removed.append(child)
            logger.debug("RMDIR: %s", child)
        except OSError:
            pass  # not empty or permission denied — skip silently (ORG-05 best-effort)


# SECTION 13 — File organization operations (Phase 2)

def _organize_games(executor: Executor, drive_root: Path, counts: dict) -> None:
    """Move contents of each console system folder into Juegos/<system>/. (ORG-03)

    Ground truth: Ordenar.ps1 lines 174-191.
    D-04: CONSOLE_SYSTEMS excludes PC and Steam — silent skip by omission.
    Moves CONTENTS of each folder, not the folder itself (Pitfall 2).
    """
    juegos_root = drive_root / "Juegos"
    for sys_name in CONSOLE_SYSTEMS:
        src_dir = drive_root / sys_name
        if not src_dir.exists():
            continue
        dst_dir = juegos_root / sys_name
        try:
            with os.scandir(src_dir) as it:
                for entry in it:
                    counts["procesados"] += 1
                    p = Path(entry.path)
                    # Check hard-block before calling executor.move — executor.move returns None
                    # for BOTH genuine OS errors AND no-touch blocks, so we must distinguish here
                    # to avoid counting normal ROM/ISO skips as errors (WR-02).
                    if is_no_touch(str(p)):
                        logger.info("SKIP (no-touch ext): %s", p)
                        counts["saltados"] += 1
                        continue
                    result = executor.move(p, dst_dir / entry.name)
                    if result is not None:
                        counts["movidos"] += 1
                    else:
                        counts["errores"] += 1
        except PermissionError:
            logger.warning("SKIP (permiso denegado): %s", src_dir)


def _move_subtitles(executor: Executor, video_src: Path, video_dst_dir: Path, counts: dict) -> None:
    """Move subtitle files sharing video_src's basename to video_dst_dir. (ORG-04)

    Ground truth: Ordenar.ps1 lines 256-268 and 296-309.
    Only called after a successful video move (Pitfall 3 — never call on failed move).
    Checks same directory as video source only — not recursive (Assumption A1).
    """
    stem = video_src.stem
    src_dir = video_src.parent
    for ext in SUB_EXTS:
        sub_src = src_dir / (stem + ext)
        if sub_src.exists():
            counts["procesados"] += 1
            result = executor.move(sub_src, video_dst_dir / sub_src.name)
            if result is not None:
                counts["movidos"] += 1
            else:
                counts["errores"] += 1


def organize_videos_and_games(executor: Executor, drive_root: Path) -> dict:
    """Organize all videos and game folders on the drive. Returns summary counter dict.

    Step 1: Move console game folder contents into Juegos/<system>/ (ORG-03).
    Step 2: Scan for video files, classify as series or movies, move to correct location (ORG-01, ORG-02).
    Step 3: Co-locate subtitles beside moved videos (ORG-04).
    Step 4: Remove empty folders (ORG-05).
    """
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)

    _organize_games(executor, drive_root, counts)

    exclude_top = SCAN_EXCLUDE_DIR_NAMES
    video_files = _scan_videos_recursive(drive_root, exclude_top)

    if not video_files:
        print("No se encontraron archivos de video para organizar.")
        return counts

    for video_path in video_files:
        counts["procesados"] += 1
        stem = video_path.stem

        m_series = RE_SERIES.match(stem)
        if m_series:
            show = m_series.group("show").strip()
            season = int(m_series.group("season"))
            dst_dir = drive_root / "Series" / show / f"Temporada {season}"
        else:
            m_movie = RE_MOVIE.match(stem)
            if m_movie:
                folder = f"{m_movie.group('title').strip()} ({m_movie.group('year')})"
            else:
                folder = stem.strip()
            dst_dir = drive_root / "Peliculas" / folder

        result = executor.move(video_path, dst_dir / video_path.name)
        if result is not None:
            counts["movidos"] += 1
            _move_subtitles(executor, video_path, result.parent, counts)
        else:
            counts["errores"] += 1

    removed = []
    _remove_empty_dirs(drive_root, removed)

    return counts


# SECTION 14 — Main menu loop and entry point

def _print_summary(counts: dict) -> None:
    """MENU-03: one-line operation summary. print() not logger (user-visible output).

    Uses [OK] ASCII marker — avoids UnicodeEncodeError on Windows cp1252 terminals.
    Field order is fixed: Procesados | Movidos | Saltados | Errores.
    """
    p = counts.get("procesados", 0)
    m = counts.get("movidos", 0)
    s = counts.get("saltados", 0)
    e = counts.get("errores", 0)
    print(f"[OK] Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")


def show_menu(executor: Executor, drive: dict) -> None:
    """Numbered main menu. Option 5 toggles dry-run (D-01). No confirmation on operation with dry-run (D-02)."""
    while True:
        dry_label = "ON" if executor.dry_run else "OFF"
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar videos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir ultima operacion")
        print("  4) Detectar incoherencias")
        print(f"  5) Dry-run: {dry_label}")
        print("  0) Salir")
        choice = input("Opcion: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            counts = organize_videos_and_games(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "2":
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "3":
            print("(Disponible en Fase 3)")
        elif choice == "4":
            print("(Disponible en Fase 4)")
        elif choice == "5":
            executor.dry_run = not executor.dry_run
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

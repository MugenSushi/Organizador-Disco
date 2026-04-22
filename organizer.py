"""Organizador de Disco — organiza discos (internos y extraibles) con medios (videos, juegos, ROMs)."""

# SECTION 1 — stdlib imports (zero external dependencies)
import ctypes
import csv
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
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
DRIVE_FIXED = 3      # GetDriveTypeW constant for fixed internal drives
DRIVE_SUPPORTED = (DRIVE_REMOVABLE, DRIVE_FIXED)  # Supported drive types

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

# Phase 5 constants - Root Organizer
DOC_EXTS: frozenset[str] = frozenset({
    ".pdf", ".csv", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf", ".html"
})

PC_GAMES_DIRS: frozenset[str] = frozenset({
    "steamlibrary", "epic games", "riot games", "amazon games", 
    "games", "launcher", "playnite", "warcraft iii", "nostale"
})

SOFTWARE_DIRS: frozenset[str] = frozenset({
    "ableton live suite 12.2.1 (x64)", 
    "image-line fl studio producer edition + signature bundle v20.7.2.1863 rc4 win", 
    "oculus"
})

# SECTION 3 — Module-level logger (before all function/class definitions)
logger = logging.getLogger("organizer")


# SECTION 4 — Drive detection helpers

def get_removable_drives() -> list[dict]:
    """Return list of dicts: [{root, label, size_gb, serial, drive_type}] for all supported drives (removable + fixed)."""
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    drives = []
    for i in range(26):
        if not (bitmask & (1 << i)):
            continue
        letter = chr(ord("A") + i)
        root = letter + ":\\"
        drive_type = kernel32.GetDriveTypeW(root)
        if drive_type not in DRIVE_SUPPORTED:
            continue
        label = _get_volume_label(kernel32, root)
        size_gb = _get_drive_size_gb(kernel32, root)
        serial = _get_volume_serial(kernel32, root)
        type_name = "Extraible" if drive_type == DRIVE_REMOVABLE else "Interno"
        drives.append({
            "root": root,
            "label": label,
            "size_gb": size_gb,
            "serial": serial,
            "type": type_name,
            "drive_type": drive_type
        })
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
        self._moves: list[dict] = []       # per-run move accumulator; cleared before each op
        self._log_serial: int = 0          # set by _prepare_executor_for_run before each op
        self._log_drive_root: str = ""     # set by _prepare_executor_for_run before each op

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
            # Accumulate for undo log — only on real moves (dry_run gated above)
            if self._log_drive_root:
                drive_root = Path(self._log_drive_root)
                try:
                    src_rel = str(src.relative_to(drive_root))
                    dst_rel = str(final_dst.relative_to(drive_root))
                except ValueError:
                    src_rel = str(src)
                    dst_rel = str(final_dst)
                self._moves.append({
                    "src": src_rel,
                    "dst": dst_rel,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                })
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
    """Select a drive (internal or removable). Implements decisions D-01, D-02, D-03 (locked)."""
    # D-02: no drives found — print error and exit (no retry loop, no manual fallback)
    if not drives:
        print("No se encontraron unidades. Asegúrate de que tienes discos conectados.")
        sys.exit(1)

    # D-01: exactly one drive — auto-select silently, no confirmation needed
    if len(drives) == 1:
        d = drives[0]
        print(f"Usando {d['root']} ({d['label']}) - {d['type']}")
        return d

    # D-03: multiple drives — numbered list: letter + label + size + type
    print("Unidades disponibles:")
    for i, d in enumerate(drives, 1):
        size_str = f"{int(d['size_gb'])} GB"
        print(f"  {i}) {d['root']} {d['label']} ({size_str}) [{d['type']}]")

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

# Phase 4 regex patterns — compiled at module level (CLAUDE.md convention)
RE_SERIES_VARIANT = re.compile(
    r"^(?P<show>.+?)[_.\s]+[Tt]emporada[_.\s]+(?P<season>\d+)[_.\s]+[Ee]pisodio[_.\s]+(?P<ep>\d+)",
    re.IGNORECASE,
)

RE_SERIES_SXXEXX = re.compile(
    r"^(?P<show>.+?)[_.\s]+[Ss](?P<season>\d{1,2})[Ee](?P<ep>\d{1,3})",
    re.IGNORECASE,
)

RE_MOVIE_VARIANT = re.compile(
    r"^(?P<title>.+?)[_.\s]+\(?(?P<year>(?:19|20)\d{2})\)?",
    re.IGNORECASE,
)

RE_NORM_STRIP = re.compile(
    r"\b(?:1080p|720p|480p|4[Kk]|2160p|x264|x265|h264|h265|avc|hevc"
    r"|bluray|blu-ray|bdrip|brrip|hdrip|webrip|web-dl|dvdrip|xvid"
    r"|hdr|sdr|dts|ac3|aac|mp3)\b",
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
            dst_dir = drive_root / "Series" / show
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


def organize_all(executor: Executor, drive_root: Path) -> dict:
    """Run all organization operations in sequence: videos/games, other files, empty cleanup."""
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)

    counts1 = organize_videos_and_games(executor, drive_root)
    for k in counts:
        counts[k] += counts1.get(k, 0)

    counts2 = organize_other_files(executor, drive_root)
    for k in counts:
        counts[k] += counts2.get(k, 0)

    _remove_empty_dirs(drive_root, [])

    return counts


def organize_other_files(executor: Executor, drive_root: Path) -> dict:
    """Move documents to DOCS, PC games to Juegos PC, and software to Software. (ORG-06, ORG-07, ORG-08)"""
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)
    docs_dir = drive_root / "DOCS"
    pc_games_dir = drive_root / "Juegos PC"
    software_dir = drive_root / "Software"

    try:
        with os.scandir(drive_root) as it:
            for entry in it:
                if should_skip_path(entry.path) or entry.name.lower() in CLEANUP_EXCLUDE_NAMES:
                    continue

                p = Path(entry.path)
                if is_no_touch(str(p)):
                    continue

                if entry.is_file(follow_symlinks=False):
                    if p.suffix.lower() in DOC_EXTS:
                        counts["procesados"] += 1
                        result = executor.move(p, docs_dir / p.name)
                        if result is not None:
                            counts["movidos"] += 1
                        else:
                            counts["errores"] += 1
                elif entry.is_dir(follow_symlinks=False):
                    name_lower = entry.name.lower()
                    if name_lower in PC_GAMES_DIRS:
                        counts["procesados"] += 1
                        result = executor.move(p, pc_games_dir / p.name)
                        if result is not None:
                            counts["movidos"] += 1
                        else:
                            counts["errores"] += 1
                    elif name_lower in SOFTWARE_DIRS:
                        counts["procesados"] += 1
                        result = executor.move(p, software_dir / p.name)
                        if result is not None:
                            counts["movidos"] += 1
                        else:
                            counts["errores"] += 1
    except PermissionError:
        logger.warning("SKIP (permiso denegado): %s", drive_root)

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


# SECTION 15 — Undo log helpers (UNDO-01, UNDO-02)

def flush_undo_log(log_path: Path, data: dict) -> None:
    """Write undo log atomically using .tmp + os.replace. No-op if moves list is empty (UNDO-01)."""
    if not data.get("moves"):
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = log_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(log_path))  # atomic on same filesystem (MoveFileExW)
    except PermissionError:
        logger.warning("No se pudo escribir el log de undo (disco de solo lectura).")
    except OSError as exc:
        logger.error("ERR escribiendo log de undo: %s", exc)


def _prepare_executor_for_run(executor: Executor, drive: dict) -> None:
    """Set per-run metadata on executor and clear move accumulator before each operation."""
    executor._log_serial = drive["serial"]
    executor._log_drive_root = drive["root"]
    executor._moves = []


def _flush_and_clear(executor: Executor, log_path: Path) -> None:
    """Write undo log atomically if this was a real run with recorded moves (UNDO-01, UNDO-02)."""
    if executor.dry_run:
        return  # dry-run: no real moves, nothing to undo (Claude's discretion)
    if not executor._moves:
        return
    data = {
        "serial": executor._log_serial,
        "drive_root": executor._log_drive_root,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "moves": executor._moves,
    }
    flush_undo_log(log_path, data)
    executor._moves = []


def undo_last_run(drive: dict, all_drives: list[dict]) -> None:
    """Revert the last logged operation. Implements UNDO-03, UNDO-02 (serial re-anchor), D-04 (skip missing).

    Reads last_run.json, matches by serial to handle drive-letter changes,
    reverts moves in reverse order, deletes log after to prevent double-undo.
    """
    # Step 1: locate last_run.json — search all drives by serial to handle letter changes (UNDO-02)
    log_data = None
    actual_log_path = None
    for d in all_drives:
        candidate = Path(d["root"]) / LOG_DIR_NAME / "last_run.json"
        if candidate.exists():
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                if raw.get("serial") == drive["serial"]:
                    log_data = raw
                    actual_log_path = candidate
                    break
            except (json.JSONDecodeError, OSError):
                continue

    # Fallback: check current drive directly (common case: letter unchanged)
    if log_data is None:
        fallback = Path(drive["root"]) / LOG_DIR_NAME / "last_run.json"
        if fallback.exists():
            try:
                log_data = json.loads(fallback.read_text(encoding="utf-8"))
                actual_log_path = fallback
            except (json.JSONDecodeError, OSError):
                pass

    if log_data is None:
        print("No hay ninguna operacion para deshacer.")
        return

    moves = log_data.get("moves", [])
    if not moves:
        print("El log no contiene movimientos para revertir.")
        return

    # Step 2: revert in reverse order (D-04: skip missing files, never abort)
    revert_root = Path(drive["root"])
    drive_root_str = str(revert_root.resolve()).lower()
    reverted = 0
    skipped = []
    errors = 0

    for entry in reversed(moves):
        src_rel = entry.get("src", "")
        dst_rel = entry.get("dst", "")
        if not src_rel or not dst_rel:
            logger.warning("UNDO: entrada ignorada — faltan campos src/dst.")
            skipped.append(dst_rel or "?")
            continue

        # Reconstruct absolute paths: src = original location, dst = current location
        src_abs = revert_root / src_rel
        dst_abs = revert_root / dst_rel

        # Path traversal guard — mirrors apply_renames() lines 296-313
        try:
            src_resolved = src_abs.resolve()
            dst_resolved = dst_abs.resolve()
        except OSError:
            logger.warning("UNDO SKIP: no se pudo resolver ruta — %s", dst_rel)
            skipped.append(dst_rel)
            continue
        src_str_low = str(src_resolved).lower()
        dst_str_low = str(dst_resolved).lower()
        if not (src_str_low.startswith(drive_root_str + "\\") or src_str_low == drive_root_str) or \
                not (dst_str_low.startswith(drive_root_str + "\\") or dst_str_low == drive_root_str):
            logger.warning(
                "UNDO SKIP (path traversal): ruta fuera de la unidad: src=%s dst=%s",
                src_resolved, dst_resolved,
            )
            skipped.append(dst_rel)
            continue

        # D-04: if file is no longer at expected dst, skip (not an error)
        if not dst_abs.exists():
            skipped.append(dst_rel)
            continue

        try:
            src_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst_abs), str(src_abs))
            reverted += 1
            logger.info("UNDO: %s -> %s", dst_abs, src_abs)
        except PermissionError:
            logger.error("UNDO DENY: %s (acceso denegado)", dst_abs)
            errors += 1
        except OSError as exc:
            logger.error("UNDO ERR: %s : %s", dst_abs, exc)
            errors += 1

    # Step 3: summary line — consistent with _print_summary [OK] ASCII style
    print(f"[OK] Revertidos: {reverted} | Saltados: {len(skipped)} | Errores: {errors}")
    if skipped:
        print("Archivos no encontrados (saltados):")
        for s in skipped:
            print(f"  {s}")

    # Step 4: delete log to prevent double-undo (Pattern 5 from RESEARCH.md)
    try:
        actual_log_path.unlink()
    except OSError:
        pass  # non-critical — log left behind is harmless


# SECTION 16 — Power features (Phase 4)

def generate_rename_plan(drive_root: Path) -> dict:
    """Scan drive and write rename_plan.tsv with proposed normalizations. (RENAME-03, RENAME-04)"""
    out_path = drive_root / LOG_DIR_NAME / "rename_plan.tsv"
    rows = []

    # Scan video files
    video_files = _scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)
    for p in video_files:
        proposal = _propose_series_rename(p.stem, p, drive_root)
        if proposal is None:
            proposal = _propose_movie_rename(p.stem, p, drive_root)
        if proposal:
            rows.append(proposal)

    # Scan for misplaced game files (outside Juegos\)
    juegos_root = drive_root / "Juegos"
    for sys_name in CONSOLE_SYSTEMS:
        sys_dir = drive_root / sys_name
        # sys_dir itself is the misplaced location — contents should be in Juegos\sys_name\
        if sys_dir.exists():
            try:
                with os.scandir(sys_dir) as it:
                    for entry in it:
                        if entry.is_file(follow_symlinks=False):
                            p = Path(entry.path)
                            if is_no_touch(str(p)) or should_skip_path(str(p)):
                                continue
                            dst = juegos_root / sys_name / p.name
                            rows.append((str(p), str(dst)))
            except PermissionError:
                logger.warning("SKIP (permiso denegado): %s", sys_dir)

    counts = {"propuestos": len(rows), "escritos": 0}
    if not rows:
        print("No se encontraron archivos para renombrar.")
        return counts

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["old_path", "new_path"])  # header
        for old, new in rows:
            writer.writerow([old, new])
    counts["escritos"] = len(rows)
    print(f"rename_plan.tsv generado: {len(rows)} propuestas -> {out_path}")
    return counts


def _propose_series_rename(stem: str, path: Path, drive_root: Path):
    """Return (old_path_str, new_path_str) if stem is a series in variant format, else None."""
    # If already canonical, skip
    if RE_SERIES.match(stem):
        return None

    m = RE_SERIES_VARIANT.match(stem)
    if not m:
        m = RE_SERIES_SXXEXX.match(stem)

    if not m:
        return None

    show = re.sub(r"[_.]", " ", m.group("show")).strip()
    season = int(m.group("season"))
    ep = int(m.group("ep"))

    if not show:  # D-02: can't infer show name → skip
        return None

    canonical = f"{show} - Temporada {season} - Episodio {ep}{path.suffix}"
    new_path = path.parent / canonical
    return (str(path), str(new_path))


def _propose_movie_rename(stem: str, path: Path, drive_root: Path):
    """Return (old_path_str, new_path_str) if stem is a movie in variant format, else None."""
    # If already canonical, skip
    if RE_MOVIE.match(stem):
        return None

    m = RE_MOVIE_VARIANT.match(stem)
    if not m:
        return None

    title = re.sub(r"[_.]", " ", m.group("title")).strip()
    year = m.group("year")

    if not title:  # D-02: can't infer title → skip
        return None

    canonical = f"{title} ({year}){path.suffix}"
    new_path = path.parent / canonical
    # Only propose if name actually changes
    if new_path.name == path.name:
        return None
    return (str(path), str(new_path))


def check_coherence(drive_root: Path) -> None:
    """Audit drive structure and report problems. (COH-01, COH-02, COH-03)"""
    series_root   = drive_root / "Series"
    peliculas_root = drive_root / "Peliculas"
    report_path   = drive_root / LOG_DIR_NAME / "coherence_report.txt"

    lines = []

    # COH-01: video files outside Series\ and Peliculas\
    outside = []
    all_videos = _scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)
    for p in all_videos:
        p_str = str(p).lower()
        if not (p_str.startswith(str(series_root).lower()) or
                p_str.startswith(str(peliculas_root).lower())):
            outside.append(p)

    lines.append(f"=== COH-01: Videos fuera de Series\\ y Peliculas\\ ({len(outside)}) ===")
    for p in outside:
        lines.append(f"  {p}")

    # COH-02: series episodes directly under Series\<show>\ without Temporada X subfolder
    unfoldered = []
    if series_root.exists():
        try:
            with os.scandir(series_root) as it:
                for show_entry in it:
                    if not show_entry.is_dir(follow_symlinks=False):
                        continue
                    show_dir = Path(show_entry.path)
                    try:
                        with os.scandir(show_dir) as show_it:
                            for ep_entry in show_it:
                                if ep_entry.is_file(follow_symlinks=False):
                                    p = Path(ep_entry.path)
                                    if p.suffix.lower() in VIDEO_EXTS:
                                        unfoldered.append(p)
                    except PermissionError:
                        logger.warning("SKIP (permiso): %s", show_dir)
        except PermissionError:
            logger.warning("SKIP (permiso): %s", series_root)

    lines.append(f"\n=== COH-02: Episodios sin carpeta Temporada ({len(unfoldered)}) ===")
    for p in unfoldered:
        lines.append(f"  {p}")

    # COH-03: duplicate titles after normalization
    seen: dict[str, list[Path]] = {}
    for p in all_videos:
        key = _normalize_for_dedup(p.stem)
        if not key:
            continue
        seen.setdefault(key, []).append(p)

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    lines.append(f"\n=== COH-03: Titulos duplicados (normalizados) ({len(duplicates)} grupos) ===")
    for key, paths in sorted(duplicates.items()):
        lines.append(f"  [{key}]")
        for p in paths:
            lines.append(f"    {p}")

    # Output to console
    for line in lines:
        print(line)

    # Output to file
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n[OK] Reporte guardado en: {report_path}")


def _normalize_for_dedup(stem: str) -> str:
    """Strip year, resolution/codec tags, lowercase, collapse spaces. (COH-03 Claude's Discretion)"""
    s = stem
    s = re.sub(r"\((?:19|20)\d{2}\)", "", s)   # strip (year)
    s = RE_NORM_STRIP.sub("", s)
    s = re.sub(r"[_.\-]+", " ", s)              # normalize separators
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def show_menu(executor: Executor, drive: dict, drives: list[dict]) -> None:
    """Numbered main menu. Option 5 toggles dry-run (D-01). No confirmation on operation with dry-run (D-02)."""
    log_path = Path(drive["root"]) / LOG_DIR_NAME / "last_run.json"
    while True:
        dry_label = "ON" if executor.dry_run else "OFF"
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print(" 1) Ordenar todo")
        print(" 2) Aplicar rename_plan.tsv")
        print(" 3) Revertir ultima operacion")
        print(" 4) Detectar incoherencias")
        print(f" 5) Dry-run: {dry_label}")
        print(" 6) Generar rename_plan.tsv")
        print(" 0) Salir")
        choice = input("Opcion: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            _prepare_executor_for_run(executor, drive)
            counts = organize_all(executor, Path(drive["root"]))
            _print_summary(counts)
            _flush_and_clear(executor, log_path)
        elif choice == "2":
            _prepare_executor_for_run(executor, drive)
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
            _flush_and_clear(executor, log_path)
        elif choice == "3":
            undo_last_run(drive, drives)
        elif choice == "4":
            check_coherence(Path(drive["root"]))
        elif choice == "5":
            executor.dry_run = not executor.dry_run
        elif choice == "6":
            generate_rename_plan(Path(drive["root"]))
        else:
            print("Opcion invalida.")


def main() -> None:
    """Script entry point. No CLI arguments required (MENU-01)."""
    logger = setup_console_logging()
    drives = get_removable_drives()
    drive = select_drive(drives)

    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)

    executor = Executor(dry_run=False)
    show_menu(executor, drive, drives)


if __name__ == "__main__":
    main()


# Technology Stack

**Project:** Organizador de Disco
**Researched:** 2026-04-19
**Confidence:** HIGH — all recommendations backed by official Python 3.x documentation

---

## Recommended Stack

All modules are Python stdlib only. No pip installs. No external dependencies.

### File System Operations

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `pathlib.Path` | 3.4+ | All path construction, stat, glob, iterdir | Object-oriented API, `/` operator for joining, `.stem`/`.suffix`/`.name` attributes, reads clean |
| `shutil` | stdlib | Move and copy files with metadata | `shutil.move()` handles cross-filesystem moves atomically when possible; `shutil.copy2()` preserves timestamps |
| `os` | stdlib | `os.replace()` for atomic overwrite, `os.makedirs(exist_ok=True)` | Needed for the few operations pathlib delegates to os under the hood |

**pathlib is the primary interface.** Use `os` only where pathlib has no direct equivalent (e.g., `os.replace` for guaranteed atomic rename, `os.makedirs`).

### Drive Detection

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `ctypes` | stdlib | Call `GetLogicalDrives` + `GetDriveTypeW` from `kernel32` | Zero subprocess overhead, no external tool dependency, pure API call |
| `subprocess` | stdlib | Fallback: `wmic logicaldisk` or PowerShell `Get-Volume` | Use only if ctypes fails (e.g., unusual Python build); adds latency |

**ctypes is the primary approach.** Subprocess is the fallback.

### Data Persistence

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `json` | stdlib | Undo log — record every move as a JSON array of `{src, dst, timestamp}` | Human-readable, trivially reversible by reading and swapping src/dst, `json.dump(indent=2, ensure_ascii=False)` for legibility |
| `csv` | stdlib | Read `rename_plan.tsv` with `delimiter='\t'` | Official TSV reading pattern; `dialect='excel-tab'` or explicit `delimiter='\t'`; always `newline=''` and `encoding='utf-8-sig'` to handle BOM from Excel |

### Pattern Matching

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `re` | stdlib | Match series/movie/ROM filenames | `re.compile()` at module level for patterns used in loops; group names over numbered groups for readability |

### Logging

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `logging` | stdlib | Operational log to `<drive>\_organizer_logs\` | Thread-safe, level-filtered, `RotatingFileHandler` prevents unbounded growth; dual output: file + console |

### Menu / CLI

| Module | Purpose | Why |
|--------|---------|-----|
| `input()` + plain `print()` | Interactive menu loop | No curses (Windows console support is broken/partial), no readline dependency; a numbered menu with a `while True` loop is the correct pattern |

---

## Module-by-Module Patterns

### pathlib — File Operations

```python
from pathlib import Path

drive = Path("F:\\")
videos = list(drive.glob("**/*.mkv"))      # recursive glob
dest = drive / "Series" / show / season
dest.mkdir(parents=True, exist_ok=True)    # create tree if missing

# Move via shutil (not Path.rename — crosses directories reliably)
import shutil
shutil.move(str(src), str(dest / src.name))
```

**Never use `Path.rename()` for the actual moves.** It raises `OSError` across drives and has unclear semantics when destination exists. Use `shutil.move()`.

**Do use Path** for everything else: existence checks, extension access (`.suffix`), parent traversal (`.parent`), name splitting (`.stem`), building destination paths.

### ctypes — Removable Drive Detection (PRIMARY)

```python
import ctypes
import string

DRIVE_REMOVABLE = 2

def get_removable_drives():
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    drives = []
    for i in range(26):
        if bitmask & (1 << i):
            letter = chr(ord('A') + i)
            path = f"{letter}:\\"
            if kernel32.GetDriveTypeW(path) == DRIVE_REMOVABLE:
                drives.append(Path(path))
    return drives
```

`GetDriveTypeW` constants:
- `0` = DRIVE_UNKNOWN
- `1` = DRIVE_NO_ROOT_DIR
- `2` = DRIVE_REMOVABLE  ← what we want
- `3` = DRIVE_FIXED
- `4` = DRIVE_REMOTE
- `5` = DRIVE_CDROM
- `6` = DRIVE_RAMDISK

**This is a pure kernel32 call — no subprocess, no shell, instant.**

### subprocess — Drive Detection (FALLBACK ONLY)

```python
import subprocess

def get_removable_drives_fallback():
    result = subprocess.run(
        ["wmic", "logicaldisk", "where", "drivetype=2", "get", "name"],
        capture_output=True, text=True, encoding="utf-8", timeout=5
    )
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
    return [Path(l + "\\") for l in lines if len(l) == 2]
```

WMIC is deprecated on Windows 11 but still present. PowerShell `Get-Volume` is more reliable but slower to launch. Use ctypes first; fall back to subprocess only if `ctypes.windll` raises `AttributeError` (unusual).

### json — Undo Log

```python
import json
from datetime import datetime
from pathlib import Path

def write_undo_log(log_path: Path, moves: list[dict]):
    """moves = [{"src": str, "dst": str, "ts": iso_str}, ...]"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(moves, f, indent=2, ensure_ascii=False)

def read_undo_log(log_path: Path) -> list[dict]:
    with open(log_path, encoding="utf-8") as f:
        return json.load(f)

# Log path convention
log_file = drive / "_organizer_logs" / f"undo_{datetime.now():%Y%m%d_%H%M%S}.json"
```

Write the entire session as one JSON array at the end, not appended line-by-line. This makes the file valid JSON (not JSONL) and keeps undo simple: `load → reverse → replay`. Use `os.replace(tmp, final)` for atomic write if data integrity matters.

### csv — TSV Reading

```python
import csv

def read_rename_plan(tsv_path: Path) -> list[dict]:
    rows = []
    with open(tsv_path, newline="", encoding="utf-8-sig") as f:  # utf-8-sig handles Excel BOM
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(dict(row))
    return rows
```

`utf-8-sig` silently strips the BOM that Excel/Notepad adds when saving as UTF-8. `csv.DictReader` uses the first row as field names. Always `newline=""` — this is mandatory per the docs, not optional.

### re — Media Filename Patterns

```python
import re

# Compile once at module level — not inside functions
RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s*-\s*Temporada\s+(?P<season>\d+)\s*-\s*Episodio\s+(?P<episode>\d+)",
    re.IGNORECASE
)
RE_MOVIE = re.compile(r"^(?P<title>.+?)\s+\((?P<year>\d{4})\)\s*$")

# ROM/ISO extensions — no regex needed, just a frozen set
ROM_EXTENSIONS = frozenset({
    ".nes", ".sfc", ".smc", ".gba", ".gbc", ".gb",
    ".nds", ".n64", ".z64", ".v64", ".iso", ".bin",
    ".cue", ".img", ".rom", ".psx", ".ps2"
})
SYSTEM_DIRS = frozenset({
    "$recycle.bin", "system volume information",
    "program files", "program files (x86)", "windows",
    "_organizer_logs"
})

def is_protected(path: Path) -> bool:
    return path.suffix.lower() in ROM_EXTENSIONS or \
           path.name.lower() in SYSTEM_DIRS
```

Use **named groups** (`?P<name>`) not numbered groups. It makes the calling code self-documenting.

### logging — Dual Output (File + Console)

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: Path, verbose: bool = False) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("organizer")
    logger.setLevel(logging.DEBUG)

    # File handler — detailed, rotating
    fh = RotatingFileHandler(
        log_dir / "organizer.log",
        maxBytes=2 * 1024 * 1024,   # 2 MB
        backupCount=3,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))

    # Console handler — INFO by default, DEBUG if verbose
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
```

**Do not use `logging.basicConfig()`** for this project. `basicConfig` configures the root logger and does nothing if any handler is already registered — it is fragile in a single-module script that grows. Use an explicit named logger (`"organizer"`) with explicit handlers instead.

### Menu Loop — input() Pattern

```python
def show_menu(options: list[tuple[str, callable]]) -> None:
    """
    options = [("Organizar Series", do_series), ("Aplicar renombrados", do_rename), ...]
    """
    while True:
        print()
        print("=" * 40)
        for i, (label, _) in enumerate(options, 1):
            print(f"  {i}. {label}")
        print("  0. Salir")
        print("=" * 40)

        choice = input("Opción: ").strip()
        if choice == "0":
            break
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            options[int(choice) - 1][1]()   # call the handler
        else:
            print(f"Opción inválida: {choice!r}")
```

**Do not use curses.** Python's `curses` module on Windows requires the `windows-curses` package (not stdlib). The built-in Windows console does not expose a curses-compatible terminal interface. Plain `input()` + `print()` is the correct approach for this use case: occasional interactive use, not a live-updating TUI.

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Path API | `pathlib` | `os.path` | `os.path` is procedural string manipulation; pathlib is idiomatic Python 3.4+, cleaner, fewer mistakes |
| Drive detection | `ctypes.windll` | `subprocess + wmic` | subprocess spawns a child process, adds 200–500ms startup time, WMIC is deprecated on Win11 |
| Drive detection | `ctypes.windll` | `subprocess + PowerShell` | PowerShell startup is even slower (~1s), and adds a dependency on PowerShell being in PATH |
| Undo log | `json` (full array) | JSONL (one entry per line) | JSONL is harder to reverse cleanly; full array is one `json.load()` call for undo |
| Undo log | `json` | `sqlite3` | Overkill for a single-session undo log; JSON is human-inspectable |
| Menu | `input()` | `curses` | curses on Windows requires `windows-curses` (not stdlib); breaks the zero-dependency constraint |
| Menu | `input()` | `argparse` | argparse is for CLI argument parsing, not interactive menus; project explicitly excluded CLI args |
| Logging | named logger + handlers | `logging.basicConfig()` | basicConfig is fragile (no-op if handlers exist), harder to configure dual output |
| Logging | `logging` module | manual `open().write()` | logging module handles rotation, levels, thread safety automatically |
| File move | `shutil.move()` | `Path.rename()` | `Path.rename()` fails across filesystems/drives and has undefined behavior when destination exists |
| TSV reading | `csv.DictReader(delimiter='\t')` | manual `line.split('\t')` | manual split breaks on quoted fields, doesn't handle edge cases |

---

## Installation

No installation required. All modules are Python stdlib.

```python
# These are all the imports the project needs — zero pip installs
import ctypes
import csv
import json
import logging
import os
import re
import shutil
import subprocess  # fallback only
import string
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
```

Python version requirement: **3.9+** (for `str | None` type hints; all modules available since 3.4+).

---

## Confidence Levels Per Recommendation

| Recommendation | Confidence | Source |
|----------------|------------|--------|
| pathlib over os.path | HIGH | Official Python docs, Python 3.4+ design intent |
| shutil.move for moves | HIGH | Official shutil docs — explicit cross-filesystem behavior documented |
| ctypes.windll for drive detection | HIGH | Official ctypes docs + GetDriveTypeW Windows API constants |
| subprocess as fallback only | HIGH | Official subprocess docs — subprocess.run patterns verified |
| json for undo log | HIGH | Official json docs — dump/load patterns verified |
| csv with dialect='excel-tab' | HIGH | Official csv docs — excel-tab dialect is registered stdlib |
| utf-8-sig encoding for TSV | MEDIUM | Standard practice for Excel-generated files; not explicitly in csv docs |
| re.compile at module level | HIGH | Official re docs — explicit recommendation for repeated use |
| named groups in regex | HIGH | Official re docs |
| input() menu over curses | HIGH | curses Windows limitation is documented; windows-curses not in stdlib |
| Named logger over basicConfig | MEDIUM | Official logging docs state basicConfig is no-op if handlers exist; recommendation inferred from docs, not explicit |
| RotatingFileHandler 2MB/3 | MEDIUM | Standard practice; specific values are project judgment calls |

---

## Sources

- https://docs.python.org/3/library/pathlib.html
- https://docs.python.org/3/library/shutil.html
- https://docs.python.org/3/library/ctypes.html
- https://docs.python.org/3/library/subprocess.html
- https://docs.python.org/3/library/json.html
- https://docs.python.org/3/library/csv.html
- https://docs.python.org/3/library/re.html
- https://docs.python.org/3/library/logging.html
- https://docs.python.org/3/library/logging.handlers.html
- https://docs.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getdrivetypew (GetDriveTypeW constants)

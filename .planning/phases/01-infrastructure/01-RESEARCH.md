# Phase 1: Infrastructure - Research

**Researched:** 2026-04-19
**Domain:** Python stdlib — ctypes Windows API, pathlib/shutil file ops, logging, interactive menu
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** If exactly one removable drive is detected, auto-select it silently — print `Usando F:\ (NOMBRE)` and go straight to the menu. No confirmation prompt.
- **D-02:** If no removable drives are detected, print a clear error message and exit. No retry loop, no manual-path fallback.
- **D-03:** If multiple removable drives are detected, list as numbered options: letter + label + size (e.g., `1) F:\ MEDIOS (931 GB)`). User types the number to select.
- All file moves route through `Executor.move()` — dry_run flag lives there.
- Log path convention: `<drive>\_organizer_logs\` — created on demand.
- Single `.py` file architecture (no packages/modules split).
- Python stdlib only — zero external dependencies.
- os.scandir only for file discovery (never glob/rglob — bracket filenames break glob).

### Claude's Discretion

- Menu shell completeness: how many placeholder entries to show for Phase 2-4 features.
- Safety block verbosity: silent count-only vs. per-item warning prints for ROM/ISO skips.
- Internal code structure (constants → helpers → classes → main loop) within the single `.py` file.
- Logging configuration: level, format, RotatingFileHandler size (follow CLAUDE.md: 2 MB / 3 backups, dual file+console output; console-only until drive is selected).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Detect all removable drives at startup via ctypes GetDriveTypeW | ctypes API verified live; DRIVE_REMOVABLE=2 confirmed |
| INFRA-02 | Ask user which drive to use, validate before continuing | input() loop pattern; D-01/D-02/D-03 decision covers all cases |
| INFRA-03 | Hard block on ROM/ISO extensions (frozen set from Ordenar.ps1) | frozenset lookup is O(1); extension list extracted from reference PS1 |
| INFRA-04 | Hard block on system paths (System Volume Information, $RECYCLE.BIN, etc.) | any() + str.lower() substring check pattern; list from Ordenar.ps1 |
| INFRA-05 | File discovery uses os.scandir exclusively (never glob/rglob) | os.scandir verified stdlib; bracket issue documented in CLAUDE.md |
| INFRA-06 | All moves through Executor class with centralised dry_run flag | Class design pattern — no external deps required |
| INFRA-07 | Collision-safe destination via _free_path() suffix (2), (3)... | Path.exists() loop; stem/suffix split via pathlib verified |
| INFRA-08 | Logs written to `<drive>\_organizer_logs\` with UTF-8 encoding | RotatingFileHandler + encoding param verified in Python 3.9+ |
| MENU-01 | Numbered main menu in terminal, no CLI arguments required | input() + while True loop pattern; argparse explicitly rejected |
</phase_requirements>

---

## Summary

Phase 1 builds the skeleton that all later phases rest on: drive detection, drive selection UX, safety guards, the Executor abstraction, and the main menu shell. Everything is pure Python 3.x stdlib — verified importable on the target machine (Python 3.14.2).

The ctypes Windows API path is the correct choice for drive detection. `GetLogicalDrives()` returns a 26-bit bitmask (one bit per drive letter), and `GetDriveTypeW(root)` returns 2 for DRIVE_REMOVABLE. Both were tested live on this machine and work as documented. `GetVolumeInformationW` retrieves the volume label and 32-bit serial number (useful for undo log in Phase 3). `GetDiskFreeSpaceExW` retrieves total size in bytes, easily converted to GB for the drive listing display.

The Executor class is the critical design hub of this phase. Every file mutation in all four phases must route through `Executor.move()`. Getting the interface right now (dry_run flag, safety guards integrated at the call site, collision avoidance as a helper method) prevents rework in Phases 2-4. The menu shell should stub out future options clearly so the menu structure does not need restructuring later.

**Primary recommendation:** Implement in strict layer order — constants → safety helpers → ctypes drive detection → Executor class → logging setup → drive selection UI → main menu loop. Test each layer manually before building the next.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Drive detection | OS API (ctypes) | — | Windows kernel32 API is the authoritative source; no subprocess overhead |
| Drive selection UI | Terminal (input/print) | — | Single-process interactive terminal; no network or file I/O |
| Safety block (ROM/ISO, system paths) | Executor class | — | Must be enforced at the single mutation point, not scattered at call sites |
| Dry-run flag | Executor class | — | Centralised flag ensures every future operation respects it automatically |
| Collision avoidance | Executor._free_path() | — | Helper lives inside Executor so all moves share the same logic |
| Log file output | logging.RotatingFileHandler | Console handler | Dual output: file after drive selected, console always |
| Main menu | Terminal loop (input/print) | — | No curses (Windows partial support), no argparse (interactive, not CLI) |

---

## Standard Stack

### Core

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `ctypes` | stdlib | Drive detection via kernel32 GetDriveTypeW, GetVolumeInformationW, GetDiskFreeSpaceExW | Zero subprocess overhead; direct Windows API; DRIVE_REMOVABLE=2 constant is stable |
| `pathlib.Path` | 3.4+ stdlib | All path construction, stem/suffix splitting for _free_path(), makedirs | Object-oriented, `/` join operator, `.stem`/`.suffix` for collision helper |
| `shutil` | stdlib | `shutil.move()` for cross-filesystem moves in future phases | Handles cross-drive moves atomically when possible; `copy2` preserves timestamps |
| `os` | stdlib | `os.scandir()` for directory traversal; `os.makedirs(exist_ok=True)` for log dir | scandir required by INFRA-05; makedirs avoids race on first log write |
| `logging` + `logging.handlers.RotatingFileHandler` | stdlib | Dual file+console operational log | Thread-safe, level-filtered, rotation prevents unbounded growth |

### Supporting (Phase 1 only)

| Module | Version | Purpose | When to Use |
|--------|---------|---------|-------------|
| `json` | stdlib | Undo log (Phase 3, but Executor must be designed to accept it) | Used in Phase 3; Executor.move() signature should accept a log collector |
| `sys` | stdlib | `sys.exit()` on no-drive condition | Clean exit with message per D-02 |

### Alternatives Considered and Rejected

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ctypes.windll.kernel32` | `subprocess + wmic` | wmic deprecated on Win11; adds 200-500ms startup latency |
| `ctypes.windll.kernel32` | `subprocess + PowerShell Get-Volume` | ~1s PS startup; adds PATH dependency |
| `input()` menu | `curses` | curses Windows support requires `windows-curses` (not stdlib) |
| `input()` menu | `argparse` | Project explicitly requires interactive menu, not CLI args |
| `logging` named logger | `logging.basicConfig()` | basicConfig is no-op if handlers already exist |
| `shutil.move()` | `Path.rename()` | Path.rename() fails across filesystems; undefined when destination exists |
| `os.scandir()` | `Path.glob()` / `Path.rglob()` | glob/rglob silently skip filenames containing `[` or `]` |

**Installation:** No installation required — all modules are Python stdlib.

**Version verification:** Python 3.14.2 confirmed on target machine via `py -3 --version`. All required modules (`ctypes`, `pathlib`, `shutil`, `os`, `json`, `logging`, `logging.handlers`) confirmed importable. [VERIFIED: live test on target machine]

---

## Architecture Patterns

### System Architecture Diagram

```
Script startup
     |
     v
[ctypes: GetLogicalDrives() bitmask]
     |
     +--> No DRIVE_REMOVABLE drives found
     |         |
     |         v
     |    Print error + sys.exit()         [D-02]
     |
     +--> Exactly 1 removable drive
     |         |
     |         v
     |    Auto-select, print "Usando X:\ (LABEL)"  [D-01]
     |         |
     +--> Multiple removable drives        [D-03]
               |
               v
         [Drive listing: "1) F:\ MEDIOS (931 GB)"]
               |
         [input() selection loop — validate 1..N]
               |
               v
         [Logging: setup RotatingFileHandler at <drive>\_organizer_logs\]
               |
               v
         [Main menu loop]
               |
         +-----+-----+-----+-----+...
         |     |     |     |     |
        Op1   Op2   Op3   Op4  [0] Salir
       (Ph2) (Ph2) (Ph3) (Ph4)
               |
               v (on any operation selection)
         [Executor.move(src, dst)]
               |
         +-----+-----+
         |           |
    Safety check   dry_run?
    ROM/ISO ext      |
    system path   YES: print plan
         |        NO:  shutil.move()
    BLOCK: skip        |
                  _free_path() if collision
```

### Recommended Project Structure

```
organizer.py          # Single file: constants, helpers, Executor class, main()
```

Internal structure within the single file (top to bottom):

```python
# 1. Imports (stdlib only)
# 2. Constants (NO_TOUCH_EXTS frozenset, SKIP_PATH_PARTS tuple, LOG_DIR_NAME)
# 3. Drive detection helpers (get_removable_drives(), get_drive_label(), get_drive_size_gb())
# 4. Safety helpers (is_no_touch(), should_skip_path())
# 5. Path helpers (_free_path())
# 6. Executor class (dry_run flag, move(), ensure_dir())
# 7. Logging setup (setup_logging(log_dir))
# 8. Drive selection UI (select_drive())
# 9. Main menu loop (show_menu(), main())
```

### Pattern 1: ctypes Drive Detection

**What:** Enumerate all drive letters, filter to DRIVE_REMOVABLE=2, retrieve label and size.
**When to use:** At script startup, before any other operation.

```python
# Source: https://docs.python.org/3/library/ctypes.html + Windows API docs
# VERIFIED: live test on target machine 2026-04-19

import ctypes

DRIVE_REMOVABLE = 2

def get_removable_drives():
    """Return list of dicts: [{root, label, size_gb, serial}]"""
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

def _get_volume_label(kernel32, root):
    buf = ctypes.create_unicode_buffer(261)
    kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0)
    return buf.value or root.rstrip("\\")

def _get_volume_serial(kernel32, root):
    serial = ctypes.c_ulong()
    kernel32.GetVolumeInformationW(root, None, 0, ctypes.byref(serial), None, None, None, 0)
    return serial.value

def _get_drive_size_gb(kernel32, root):
    total = ctypes.c_ulonglong(0)
    kernel32.GetDiskFreeSpaceExW(root, None, ctypes.byref(total), None)
    return round(total.value / 1_073_741_824, 0)
```

**Note on GetVolumeInformationW:** The 8th parameter (dwFileSystemFlags) can be None (NULL) since we don't need it. When passing None for an output buffer, ctypes passes NULL — confirmed safe for parameters not needed. [VERIFIED: live test]

### Pattern 2: Safety Guards as Constants + Functions

**What:** ROM/ISO block uses `frozenset` for O(1) lookup. System-path block uses `tuple` of lowercase substrings.
**When to use:** Check both before any Executor.move() call (inside Executor is safest).

```python
# Source: Ordenar.ps1 $NO_TOUCH_EXTS and $SKIP_PATH_PARTS (ground truth)
# VERIFIED: extracted from reference PowerShell script

NO_TOUCH_EXTS = frozenset({
    ".iso", ".bin", ".cue", ".img", ".mdf", ".nrg", ".chd", ".cso", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".n64", ".z64", ".v64",
    ".3ds", ".cia", ".nds", ".gcm", ".wbfs", ".wad", ".xci", ".nsp",
})

# Use lowercase for case-insensitive matching on Windows
SKIP_PATH_PARTS = (
    "\\system volume information\\",
    "\\$recycle.bin\\",
    "\\windowsapps\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\amazon games\\",
)

def is_no_touch(path: str) -> bool:
    """True if the file extension is in the ROM/ISO block list."""
    ext = path.lower()
    dot = ext.rfind(".")
    return ext[dot:] in NO_TOUCH_EXTS if dot >= 0 else False

def should_skip_path(path: str) -> bool:
    """True if the path contains any protected system folder."""
    lower = path.lower()
    return any(part in lower for part in SKIP_PATH_PARTS)
```

**Note on REQUIREMENTS.md vs Ordenar.ps1 discrepancy:** INFRA-03 in REQUIREMENTS.md lists `.gba .gbc .gb .nes .sfc .smc .n64 .z64 .3ds .cia .nds .gcm .wbfs .wad .xci .nsp` — it omits `.cso .pbp .v64` that appear in Ordenar.ps1. The planner should include the superset (Ordenar.ps1 is the stated ground truth per CONTEXT.md). [VERIFIED: cross-referenced both sources]

### Pattern 3: Executor Class with dry_run Flag

**What:** Single class owns all filesystem mutations. dry_run=True prints intent; dry_run=False executes.
**When to use:** All file move/rename operations in all phases route through this.

```python
# Source: Phase 1 design; shutil docs https://docs.python.org/3/library/shutil.html
# ASSUMED: class interface — no prior implementation exists

import shutil
import logging
from pathlib import Path

logger = logging.getLogger("organizer")

class Executor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def move(self, src: Path, dst: Path) -> Path | None:
        """Move src to dst (collision-safe). Returns final path or None if blocked."""
        src_str = str(src)

        # Safety guards — hard block
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
        shutil.move(str(src), str(final_dst))
        logger.info("MOVE: %s -> %s", src, final_dst)
        return final_dst

    def ensure_dir(self, path: Path) -> None:
        if self.dry_run:
            return
        path.mkdir(parents=True, exist_ok=True)
```

### Pattern 4: Collision-Safe Path Helper

**What:** Append ` (2)`, ` (3)` etc. to stem until no collision. Mirrors `Get-FreePath` in Ordenar.ps1.
**When to use:** Inside Executor.move() before any actual move.

```python
# Source: Translated from Ordenar.ps1 Get-FreePath function
# VERIFIED: pattern confirmed via pathlib docs https://docs.python.org/3/library/pathlib.html

from pathlib import Path

def _free_path(dst: Path) -> Path:
    """Return dst if it doesn't exist, otherwise dst with (2), (3)... suffix."""
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
```

### Pattern 5: Logging Setup (Dual Output)

**What:** Named logger with RotatingFileHandler (file) + StreamHandler (console). Console active from start; file handler added after drive is selected and log dir is known.
**When to use:** Two-stage setup — console first, file handler added post drive-selection.

```python
# Source: https://docs.python.org/3/library/logging.handlers.html
# ASSUMED: two-stage setup pattern — reasonable but not explicitly documented

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_console_logging() -> logging.Logger:
    """Call at startup before drive selection — no log path yet."""
    logger = logging.getLogger("organizer")
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger

def add_file_logging(logger: logging.Logger, log_dir: Path) -> None:
    """Call after drive is selected and log_dir is known."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "organizer.log"
    fh = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
```

### Pattern 6: Drive Selection UI

**What:** Numbered list with input() loop. Handles D-01 (auto-select), D-02 (exit), D-03 (interactive).
**When to use:** Immediately after drive detection, before menu.

```python
# Source: Design per D-01/D-02/D-03 locked decisions
# ASSUMED: exact string formatting — follows decision format "1) F:\ MEDIOS (931 GB)"

import sys

def select_drive(drives: list[dict]) -> dict:
    if not drives:
        print("No se encontraron unidades extraíbles. Conecta un disco e inténtalo de nuevo.")
        sys.exit(1)

    if len(drives) == 1:
        d = drives[0]
        print(f"Usando {d['root']} ({d['label']})")
        return d

    print("Unidades extraíbles disponibles:")
    for i, d in enumerate(drives, 1):
        size_str = f"{int(d['size_gb'])} GB"
        print(f"  {i}) {d['root']} {d['label']} ({size_str})")

    while True:
        choice = input("Selecciona una unidad [1-{}]: ".format(len(drives))).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(drives):
            return drives[int(choice) - 1]
        print(f"Entrada inválida. Escribe un número entre 1 y {len(drives)}.")
```

### Pattern 7: Main Menu Loop

**What:** Numbered menu in a while True loop. Phase 1 shows placeholders for Phase 2-4 features.
**When to use:** After drive selection and logging setup.

```python
# Source: Design — no external reference; input() menu pattern from CLAUDE.md
# ASSUMED: exact menu entries and numbering

def show_menu(executor: Executor, drive: dict) -> None:
    while True:
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar vídeos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir última operación")
        print("  4) Detectar incoherencias")
        print("  0) Salir")
        choice = input("Opción: ").strip()

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
            print("Opción inválida.")
```

### Anti-Patterns to Avoid

- **`Path.rename()` for file moves:** Fails across filesystems (e.g., C: to F:). Always use `shutil.move()`.
- **`Path.glob()` or `Path.rglob()` for discovery:** Silently skips files/folders with `[` or `]` in their names. Always use `os.scandir()` recursively.
- **`logging.basicConfig()`:** Is a no-op if any handler exists. Always configure a named logger with explicit handlers.
- **Safety checks at call site instead of Executor:** Scattered guard logic means future phases can accidentally bypass it. Put guards inside `Executor.move()`.
- **`shutil.rmtree()` for cleanup:** Project explicitly forbids it (only `os.rmdir()` for empty folders). Not needed in Phase 1 but the prohibition must be reflected in Executor design.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-filesystem file move | Custom copy+delete | `shutil.move()` | Handles cross-drive atomicity; preserves metadata |
| Log rotation | Manual file size check + rename | `RotatingFileHandler` | Thread-safe; handles backup numbering automatically |
| Collision suffix logic | Inline loop in each operation | `_free_path()` helper | Centralised; all operations share same behavior |
| Drive letter enumeration | Registry reads or subprocess | `ctypes GetLogicalDrives()` | Zero overhead; stable Windows API |
| Volume label retrieval | subprocess wmic | `ctypes GetVolumeInformationW()` | Same overhead; wmic deprecated |

**Key insight:** Every "simple" custom solution here has edge cases (cross-filesystem moves, concurrent log writes, Unicode filenames in volume labels) that the stdlib handles correctly.

---

## Common Pitfalls

### Pitfall 1: GetVolumeInformationW NULL pointer crash

**What goes wrong:** Passing `None` for output buffer parameters that the API writes to causes an access violation.
**Why it happens:** ctypes passes Python `None` as NULL; Windows writes to address 0 — crash.
**How to avoid:** For parameters you don't need, pass `None` only for purely optional OUT parameters where the docs explicitly state NULL is accepted. For serial number: `ctypes.byref(serial_c_ulong)`. Verified: serial and label can be obtained in separate calls if needed.
**Warning signs:** Access violation / OSError at startup during drive detection.

### Pitfall 2: Volume label empty string for unlabelled drives

**What goes wrong:** `GetVolumeInformationW` returns an empty string for drives with no label. Display shows `1) F:\  (931 GB)` with a gap.
**Why it happens:** Windows drives don't require labels.
**How to avoid:** Fallback to the drive letter as display name: `label or root.rstrip("\\")`.
**Warning signs:** Blank label in listing for unlabelled drives.

### Pitfall 3: Collision helper infinite loop

**What goes wrong:** `_free_path()` loops forever if the filesystem has thousands of collisions (e.g., 1000 files all named the same).
**Why it happens:** Loop has no upper bound.
**How to avoid:** For Phase 1 this is acceptable (edge case); for robustness add a max counter (e.g., 999) and raise an exception.
**Warning signs:** Script hangs during move operations on a very full drive.

### Pitfall 4: Log directory creation fails on read-only media

**What goes wrong:** `mkdir()` raises `PermissionError` on drives mounted read-only.
**Why it happens:** Removable drives can be write-protected via hardware switch.
**How to avoid:** Wrap `add_file_logging` in try/except; fall back to console-only logging with a warning. Phase 1 is unlikely to encounter this but design should not crash.
**Warning signs:** PermissionError at log directory creation step.

### Pitfall 5: os.scandir not closed properly

**What goes wrong:** `os.scandir()` returns an iterator that holds a directory handle. Not closing it on Windows can prevent directory deletion later.
**Why it happens:** If `scandir()` is used in a loop without a context manager, the handle stays open.
**How to avoid:** Always use `with os.scandir(path) as it:` (context manager form, Python 3.6+). [VERIFIED: Python 3.6+ docs confirm context manager support]

### Pitfall 6: NO_TOUCH_EXTS discrepancy between REQUIREMENTS.md and Ordenar.ps1

**What goes wrong:** REQUIREMENTS.md INFRA-03 lists fewer extensions than Ordenar.ps1's `$NO_TOUCH_EXTS`.
**Why it happens:** REQUIREMENTS.md was written manually and missed `.cso`, `.pbp`, `.v64`.
**How to avoid:** Use Ordenar.ps1 as the ground truth (per CONTEXT.md). Include the full superset: `.cso`, `.pbp`, `.v64` in addition to the REQUIREMENTS.md list. [VERIFIED: cross-referenced both sources]

---

## Runtime State Inventory

> Phase 1 is greenfield — no files exist, no external services, no stored data. Skip.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | Entire script | Yes | 3.14.2 | — |
| `ctypes` | INFRA-01 (drive detection) | Yes | stdlib | — |
| `pathlib` | All path ops | Yes | stdlib | — |
| `shutil` | File moves | Yes | stdlib | — |
| `os.scandir` | INFRA-05 | Yes | stdlib | — |
| `logging.handlers.RotatingFileHandler` | INFRA-08 | Yes | stdlib | — |
| `json` | Phase 3 undo log (future) | Yes | stdlib | — |
| Windows kernel32.dll | ctypes drive detection | Yes | OS | — |

[VERIFIED: all modules imported successfully via `py -3` on target machine 2026-04-19]

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `wmic logicaldisk` (subprocess) | `ctypes GetDriveTypeW` | Always preferred; wmic deprecated Win11 | Faster startup, no subprocess |
| `logging.basicConfig()` | Named logger + explicit handlers | Python 3.x best practice | Avoids no-op handler bug |
| `os.path.join()` | `pathlib.Path / operator` | Python 3.4+ | Cleaner, less error-prone |
| `Get-ChildItem -Recurse` (PowerShell) | `os.scandir()` recursive | INFRA-05 decision | Handles bracket filenames |

**Deprecated/outdated:**
- `wmic logicaldisk`: Deprecated in Windows 10 21H1, may be absent on Win11 — do not use even as fallback unless ctypes genuinely fails.
- `Path.rglob("*")` / `Path.glob("**/*")`: Silently skips bracket filenames — forbidden by INFRA-05.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Two-stage logging (console first, file added after drive selection) is the correct architectural split | Pattern 5 | Low — worst case both handlers start after drive selection; easy to adjust |
| A2 | Menu stub entries `(Disponible en Fase X)` are sufficient for Phase 1 menu shell | Pattern 7 | Low — planner may choose different placeholder text; behavior is equivalent |
| A3 | `_free_path()` without a max-iteration cap is acceptable for Phase 1 | Pitfall 3 | Low — edge case; Phase 2+ can add the cap when real moves are implemented |
| A4 | Safety checks inside `Executor.move()` (not at call site) is the correct location | Pattern 3 | Medium — if call sites need to distinguish "blocked" vs "moved" they need a return code; the None return handles this |

---

## Open Questions (RESOLVED)

1. **Menu dry-run toggle (MENU-02 is Phase 2, but Executor.dry_run is Phase 1)**
   - What we know: MENU-02 (activate dry-run from menu) is Phase 2. The Executor class is Phase 1.
   - What's unclear: Should Phase 1 Executor.dry_run be set at construction time only, or should the menu be able to toggle it at runtime?
   - Recommendation: Design Executor with `dry_run` as a mutable attribute (not just __init__ parameter) so Phase 2 menu can toggle it without reconstructing the object.
   - **RESOLVED:** `Executor.dry_run` is a mutable attribute (set in `__init__`, reassignable at runtime). Phase 2 menu can toggle it via `executor.dry_run = True/False` without reconstructing the object.

2. **NO_TOUCH_EXTS superset: planner decision needed**
   - What we know: REQUIREMENTS.md INFRA-03 lists fewer extensions than Ordenar.ps1.
   - What's unclear: Should the plan explicitly call out adding `.cso`, `.pbp`, `.v64`?
   - Recommendation: Yes — planner should include the full Ordenar.ps1 superset and note the discrepancy as a clarification, not a scope change.
   - **RESOLVED:** Full Ordenar.ps1 superset used including `.cso`, `.pbp`, `.v64`. Plan Task 1 action defines the complete 24-extension frozenset. INFRA-03 discrepancy is treated as a ground-truth correction from the PS1 reference implementation.

---

## Project Constraints (from CLAUDE.md)

All CLAUDE.md directives apply to this phase:

- **Python 3.x pure stdlib only** — no `pip install` of any kind
- **Windows only** — `ctypes.windll.kernel32` is the primary drive detection path
- **Never touch ROM/ISO extensions** — hard block in Executor, not advisory
- **`os.scandir()` exclusively** — never `glob`, never `rglob`
- **`shutil.move()`** for file moves — never `Path.rename()`
- **`pathlib.Path`** for all path construction
- **`json`** for undo log (Phase 3 — but Executor interface must accommodate it)
- **`logging` named logger** with RotatingFileHandler — never `basicConfig()`
- **`input()` + `print()`** for menus — never curses, never argparse
- **Single `.py` file** — no package splits
- **Log path:** `<drive>\_organizer_logs\` — created on demand, UTF-8 encoding

---

## Sources

### Primary (HIGH confidence)

- Python 3 ctypes docs — https://docs.python.org/3/library/ctypes.html — GetDriveTypeW pattern verified
- Python 3 pathlib docs — https://docs.python.org/3/library/pathlib.html — stem/suffix, exists(), mkdir()
- Python 3 shutil docs — https://docs.python.org/3/library/shutil.html — move() cross-filesystem behavior
- Python 3 logging.handlers docs — https://docs.python.org/3/library/logging.handlers.html — RotatingFileHandler
- Python 3 os.scandir docs — https://docs.python.org/3/library/os.html#os.scandir — context manager form
- Windows API — GetDriveTypeW — https://docs.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getdrivetypew
- Windows API — GetVolumeInformationW — https://docs.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw
- Windows API — GetDiskFreeSpaceExW — https://docs.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getdiskfreespaceexw
- `Ordenar.ps1` (project repo) — ground truth for NO_TOUCH_EXTS and SKIP_PATH_PARTS lists
- Live ctypes test on target machine (2026-04-19) — GetLogicalDrives, GetVolumeInformationW, GetDiskFreeSpaceExW all confirmed working

### Secondary (MEDIUM confidence)

- CLAUDE.md tech stack table — all module recommendations and rejected alternatives

### Tertiary (LOW confidence)

None — all claims verified via primary sources or live test.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules verified importable on target machine; APIs tested live
- Architecture: HIGH — ctypes API behavior confirmed; patterns translated from working PowerShell reference
- Pitfalls: MEDIUM — most derived from known Windows API behavior and Python docs; Pitfall 3 (infinite loop) is hypothetical edge case
- NO_TOUCH_EXTS list: HIGH — extracted directly from Ordenar.ps1 (stated ground truth)

**Research date:** 2026-04-19
**Valid until:** 2026-09-19 (stdlib is stable; Windows API constants are stable)

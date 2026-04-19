# Architecture Patterns

**Domain:** Single-file Python CLI media organizer (Windows, stdlib only)
**Researched:** 2026-04-19
**Confidence:** HIGH — patterns are well-established for this class of tool

---

## Recommended Architecture

### Guiding Constraint

Everything lives in one `.py` file. The architecture goal is not "how to split files" but "how to
draw clear internal seams so any section can be read, tested, and changed without touching the
others." The answer is layered functions + one thin class per stateful concern.

### Layers (top to bottom)

```
┌─────────────────────────────────────────────────────────┐
│                      ENTRY POINT                        │
│  main() → detect drives → select drive → main_menu()   │
└──────────────────────┬──────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────┐
│                    MENU / UI LAYER                      │
│  main_menu()   show_menu()   ask_yes_no()               │
│  prompt_choice()   print_table()   confirm_action()     │
└──────────────────────┬──────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────┐
│                  OPERATIONS LAYER                       │
│  op_rename_from_tsv()   op_organize_series()            │
│  op_organize_movies()   op_organize_games()             │
│  op_generate_tsv()      op_cleanup_empty_dirs()         │
│  op_coherence_check()   op_undo()                       │
│                                                         │
│  Each op builds a list[Action] then calls Executor      │
└───────────┬───────────────────────┬─────────────────────┘
            │                       │
┌───────────▼───────┐   ┌───────────▼─────────────────────┐
│   SCANNER / RULES │   │         EXECUTOR                │
│                   │   │                                  │
│  scan_drive()     │   │  class Executor:                 │
│  is_no_touch()    │   │    dry_run: bool                 │
│  is_protected()   │   │    undo_log: UndoLog             │
│  parse_series()   │   │    def move(src, dst)            │
│  parse_movie()    │   │    def rename(src, new_name)     │
│  parse_game_dir() │   │    def mkdir(path)               │
│  free_path()      │   │    def rmdir(path)               │
└───────────────────┘   └───────────┬─────────────────────┘
                                    │ writes
                        ┌───────────▼─────────────────────┐
                        │          UNDO LOG               │
                        │  class UndoLog:                  │
                        │    path: Path                    │
                        │    entries: list[dict]           │
                        │    def record(entry)             │
                        │    def commit()   (flush JSON)   │
                        │    def load()                    │
                        │    def replay_reverse()          │
                        └─────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    CROSS-CUTTING                        │
│  CONFIG (module-level constants)                        │
│  Logger  (thin wrapper around logging stdlib module)    │
│  DriveDetector (ctypes + os, returns list[DriveInfo])   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `main()` | Entry point, drive selection, hand off to menu | Menu layer |
| Menu layer | Print options, capture input, call ops | Operations layer |
| Operations layer | Orchestrate one feature end-to-end, build Action list | Scanner, Executor |
| Scanner / Rules | Identify files, classify, generate candidate moves | Operations layer |
| Executor | Apply or simulate each Action; write undo entries | UndoLog, filesystem |
| UndoLog | Persist and replay move history | Executor, op_undo |
| Config (constants) | Drive safety lists, extension sets, path constants | All layers (read-only) |
| Logger | Append to `<drive>\_organizer_logs\run_YYYYMMDD.log` | All layers |
| DriveDetector | Enumerate removable drives via ctypes/WMI | main() |

---

## Data Flow

```
                        User picks menu item
                               │
                    Operations layer called
                               │
                    Scanner walks drive tree
                    returns list[FileCandidate]
                               │
                    Operations layer applies
                    rules → list[Action]
                    e.g. Action(op="move",
                                src=Path(...),
                                dst=Path(...))
                               │
                    Executor receives list[Action]
                               │
                  ┌────────────┴────────────┐
           dry_run=True              dry_run=False
                  │                         │
         Print preview table        Execute each Action
         No filesystem changes        shutil.move / rename
                                            │
                                    UndoLog.record(entry)
                                            │
                                    UndoLog.commit()
                                    (atomic JSON write)
                                            │
                                    Logger.info(result)
```

---

## The Executor Pattern — Dry-Run as First-Class Concern

Dry-run must not be an `if dry_run: print(...)` scattered across every function. Instead, all
filesystem mutations route through a single `Executor` object. The dry-run flag lives only there.

```python
class Executor:
    def __init__(self, dry_run: bool, undo_log: "UndoLog"):
        self.dry_run = dry_run
        self.undo_log = undo_log
        self.stats = {"moved": 0, "renamed": 0, "skipped": 0, "errors": 0}

    def move(self, src: Path, dst: Path) -> bool:
        dst = self._free_path(dst)
        if self.dry_run:
            print(f"  [DRY] MOVE  {src}  →  {dst}")
            return True
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            self.undo_log.record({"op": "move", "src": str(src), "dst": str(dst)})
            self.stats["moved"] += 1
            return True
        except PermissionError as e:
            logger.warning(f"PERMISSION DENIED: {src}: {e}")
            self.stats["errors"] += 1
            return False
        except OSError as e:
            logger.warning(f"OS ERROR moving {src}: {e}")
            self.stats["errors"] += 1
            return False

    def rename(self, path: Path, new_name: str) -> bool:
        dst = path.parent / new_name
        dst = self._free_path(dst)
        if self.dry_run:
            print(f"  [DRY] RENAME {path.name}  →  {dst.name}")
            return True
        try:
            path.rename(dst)
            self.undo_log.record({"op": "rename", "src": str(path), "dst": str(dst)})
            self.stats["renamed"] += 1
            return True
        except PermissionError as e:
            logger.warning(f"PERMISSION DENIED: {path}: {e}")
            self.stats["errors"] += 1
            return False

    def mkdir(self, path: Path) -> None:
        if self.dry_run:
            return
        path.mkdir(parents=True, exist_ok=True)

    def rmdir_if_empty(self, path: Path) -> bool:
        if self.dry_run:
            print(f"  [DRY] RMDIR {path}")
            return True
        try:
            path.rmdir()  # only removes if actually empty
            self.undo_log.record({"op": "rmdir", "path": str(path)})
            return True
        except OSError:
            return False

    def _free_path(self, path: Path) -> Path:
        """Return path unchanged if free, else suffix with (2), (3), etc."""
        if not path.exists():
            return path
        stem, suffix = path.stem, path.suffix
        i = 2
        while True:
            candidate = path.parent / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
            i += 1
```

Operations never call `shutil.move` or `Path.rename` directly. Everything goes through Executor.
This gives you:
- Dry-run for free on every operation
- A single place to add progress bars, rate limiting, or verbose logging later
- Consistent undo-log coverage — nothing can move a file without recording it

---

## Undo Log Schema

The undo log is a JSON file at `<drive>\_organizer_logs\undo_YYYYMMDD_HHMMSS.json`.

### Top-level structure

```json
{
  "version": 1,
  "run_id": "20260419_143022",
  "drive_root": "F:\\",
  "operation": "organize_series",
  "started_at": "2026-04-19T14:30:22",
  "completed_at": "2026-04-19T14:30:45",
  "entries": [...]
}
```

### Entry types

```json
// Move
{
  "op": "move",
  "seq": 1,
  "src": "F:\\Breaking Bad - Temporada 1 - Episodio 01.mkv",
  "dst": "F:\\Series\\Breaking Bad\\Temporada 1\\Breaking Bad - Temporada 1 - Episodio 01.mkv",
  "ts":  "2026-04-19T14:30:23"
}

// Rename (same directory)
{
  "op": "rename",
  "seq": 2,
  "src": "F:\\Videos\\Breaking.Bad.S01E01.mkv",
  "dst": "F:\\Videos\\Breaking Bad - Temporada 1 - Episodio 01.mkv",
  "ts":  "2026-04-19T14:30:24"
}

// Directory created (needed so undo can remove it)
{
  "op": "mkdir",
  "seq": 3,
  "path": "F:\\Series\\Breaking Bad\\Temporada 1",
  "ts":   "2026-04-19T14:30:23"
}

// Directory removed (cleanup step — undo must recreate it if needed)
{
  "op": "rmdir",
  "seq": 4,
  "path": "F:\\OldFolder",
  "ts":   "2026-04-19T14:30:44"
}
```

### Reversal order

Undo iterates entries in **reverse seq order** (highest seq first). This ensures:
- Files are moved back before the directories that held them are removed
- Directories created during the run are deleted after files have been moved out of them

For `move` and `rename`: `shutil.move(dst, src)` — swap dst/src.
For `mkdir`: `path.rmdir()` (only if now empty, otherwise leave it).
For `rmdir`: `path.mkdir(parents=True, exist_ok=True)` — recreate.

### UndoLog class sketch

```python
class UndoLog:
    def __init__(self, log_dir: Path, operation_name: str, drive_root: Path):
        import datetime, uuid
        self._run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = log_dir / f"undo_{self._run_id}.json"
        self._data = {
            "version": 1,
            "run_id": self._run_id,
            "drive_root": str(drive_root),
            "operation": operation_name,
            "started_at": datetime.datetime.now().isoformat(),
            "completed_at": None,
            "entries": [],
        }
        self._seq = 0

    def record(self, entry: dict) -> None:
        self._seq += 1
        entry["seq"] = self._seq
        entry["ts"] = __import__("datetime").datetime.now().isoformat()
        self._data["entries"].append(entry)

    def commit(self) -> None:
        """Write final JSON atomically (write to .tmp then rename)."""
        import json, datetime
        self._data["completed_at"] = datetime.datetime.now().isoformat()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)  # atomic on same filesystem

    def load(self, path: Path) -> None:
        import json
        self._data = json.loads(path.read_text(encoding="utf-8"))

    def replay_reverse(self, executor: "Executor") -> None:
        for entry in reversed(self._data["entries"]):
            op = entry["op"]
            if op in ("move", "rename"):
                src, dst = Path(entry["dst"]), Path(entry["src"])
                if src.exists():
                    executor.move(src, dst)
                else:
                    print(f"  [UNDO SKIP] Not found: {src}")
            elif op == "mkdir":
                p = Path(entry["path"])
                try:
                    p.rmdir()
                except OSError:
                    pass  # not empty or already gone — leave it
            elif op == "rmdir":
                Path(entry["path"]).mkdir(parents=True, exist_ok=True)
```

---

## State Management: Memory vs Disk

| State | Where | Rationale |
|-------|-------|-----------|
| Selected drive root (`drive_root`) | Module-level variable set at startup | Needed by every operation; safe to hold in memory for one session |
| Dry-run flag (`dry_run`) | Passed into Executor at construction | Explicit, not global; avoids invisible side effects |
| Current operation's Action list | Local variable in each `op_*` function | Short-lived; discarded after Executor runs it; no need to persist |
| Undo entries during a run | `UndoLog._data["entries"]` (in-memory list) | Accumulated during run, flushed atomically at end via `commit()` |
| Completed undo logs | JSON files on disk | Persisted for future undo; one file per run |
| Logger output | Disk (log file) + stdout | Immediate disk write so nothing is lost on crash |
| TSV rename plan | Disk file, read fresh each apply | User may edit it between generate and apply; always re-read |

Avoid global mutable state except `drive_root` and the logger instance. Everything else travels
as function arguments or lives in the two stateful classes (Executor, UndoLog).

---

## Configuration (Module-Level Constants)

At the top of the file, before any functions, declare all tunable values as module-level
constants. This acts as the project's config section without needing a config file.

```python
# --- Safety: never touch these ---
NO_TOUCH_EXTS = frozenset({
    ".iso", ".bin", ".cue", ".img", ".mdf", ".nrg", ".chd", ".cso", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".n64", ".z64", ".v64",
    ".3ds", ".cia", ".nds", ".gcm", ".wbfs", ".wad", ".xci", ".nsp",
})

SKIP_PATH_PARTS = (
    "\\System Volume Information\\",
    "\\$RECYCLE.BIN\\",
    "\\WindowsApps\\",
    "\\Program Files\\",
    "\\Program Files (x86)\\",
    "\\Amazon Games\\",
)

# --- Media types we do organize ---
VIDEO_EXTS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".mpg", ".mpeg", ".ts"})
SUB_EXTS   = frozenset({".srt", ".ass", ".sub", ".idx"})

# --- Game systems ---
GAME_SYSTEMS = ("PC", "PS1", "PS2", "PSP", "GBA", "GBC")

# --- Output folders ---
SERIES_FOLDER   = "Series"
PELICULAS_FOLDER = "Peliculas"
JUEGOS_FOLDER   = "Juegos"
LOGS_FOLDER     = "_organizer_logs"
TSV_FILENAME    = "rename_plan.tsv"

# --- Scan exclusions (relative to drive root) ---
SCAN_EXCLUDE_DIRS = (LOGS_FOLDER, "_ORIG", JUEGOS_FOLDER)
```

Frozen sets for extension lookups give O(1) membership tests and prevent accidental mutation.

---

## Error Handling Strategy

### Principle: continue-on-error, collect and report

A single locked or missing file must never abort the entire operation. The pattern is:

1. Per-file errors are caught inside `Executor.move()` / `Executor.rename()` — log and return `False`
2. Operations track `errors` in `executor.stats`
3. After the operation finishes, print a summary: "42 moved, 1 skipped (permission denied)"
4. Fatal errors (drive disappeared, log dir not writable) raise and bubble to `main()`

### Error categories

| Error | Handling |
|-------|----------|
| `PermissionError` on a file | Log warning, skip that file, continue |
| `FileNotFoundError` (source gone) | Log warning, skip, continue |
| `FileExistsError` (dst conflict) | `free_path()` prevents this before the call |
| Drive not found at startup | Raise with clear message, exit gracefully |
| Log dir not writable | Raise with clear message, exit gracefully |
| TSV parse error (malformed row) | Log and skip that row |
| Undo target already moved back | Log "already at source, skipping" |
| `OSError` on `rmdir` (dir not empty) | Leave directory, log notice — not an error |

### Partial failures and the undo log

Undo logs are written **incrementally** — each successful move is recorded before the next
one starts. If the process is killed mid-operation, the undo log contains every move that
actually happened. On next run, op_undo() can still reverse what was done.

The `commit()` call at the end is for marking the run as `completed`. An incomplete undo log
(missing `completed_at`) is still valid for undo; the reversal is idempotent.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: `if dry_run` scattered everywhere
**What goes wrong:** Every new operation needs its own dry-run check. Developers forget. Tests
can't verify dry-run behaviour without mocking the filesystem.
**Instead:** All mutations through Executor. `dry_run` flag is invisible to operations layer.

### Anti-Pattern 2: Appending text to undo log
**What goes wrong:** Mid-write crash leaves malformed JSON. No atomic guarantee. Hard to parse
for undo.
**Instead:** Accumulate in memory during run, write one JSON file atomically via `.tmp` + rename.

### Anti-Pattern 3: Global mutable `dry_run` flag
**What goes wrong:** Impossible to run two operations with different modes (e.g. preview one,
apply another). Functions have invisible coupling.
**Instead:** Pass Executor explicitly; dry_run is Executor state.

### Anti-Pattern 4: Walking the full drive for every operation
**What goes wrong:** Slow on large drives. Re-scanning for series, then again for movies.
**Instead:** `scan_drive()` does one pass and returns classified buckets. Operations receive the
bucket they need.

### Anti-Pattern 5: Assuming `shutil.move` is atomic
**What goes wrong:** Cross-device moves are copy+delete. On crash mid-copy, you have a partial
file at dst and the original at src. Undo log shows a completed move that wasn't.
**Instead:** For moves within the same drive (`src.drive == dst.drive`), use `Path.rename()` which
is atomic at the OS level. Fall back to `shutil.move` only for cross-drive (unlikely here since
everything stays on the same removable drive, but defensible to check).

---

## Suggested Build Order

Dependencies flow from bottom up. Build each layer before the one that depends on it.

```
Step 1 ── Config constants + Safety guards
         is_no_touch(), is_protected_path(), free_path()
         ↓ (no deps, pure functions, testable immediately)

Step 2 ── DriveDetector
         detect_removable_drives() → list of (letter, label, free_gb)
         ↓ (depends only on ctypes/os)

Step 3 ── Logger + Log directory setup
         setup_logger(log_dir) → logging.Logger
         ↓ (needed by everything below)

Step 4 ── UndoLog class
         record(), commit(), load(), replay_reverse()
         ↓ (depends on: log dir)

Step 5 ── Executor class
         move(), rename(), mkdir(), rmdir_if_empty()
         ↓ (depends on: UndoLog, Logger, safety guards)

         *** At this point you can manually test the full
             move+undo cycle with hardcoded paths ***

Step 6 ── Scanner / Classifiers
         scan_drive() → {series: [], movies: [], games: {}, orphans: []}
         parse_series_name(), parse_movie_name(), parse_game_dir()
         ↓ (depends on: Config constants)

Step 7 ── op_rename_from_tsv()   [highest value, existing workflow]
         ↓ (depends on: Executor, Logger, TSV path from Config)

Step 8 ── op_organize_series()
         op_organize_movies()
         op_organize_games()
         ↓ (depends on: Scanner, Executor)

Step 9 ── op_cleanup_empty_dirs()
         op_coherence_check()    [read-only, no Executor needed]
         ↓ (depends on: Scanner)

Step 10 ── op_generate_tsv()    [pure scan + write, no Executor]
          ↓ (depends on: Scanner)

Step 11 ── op_undo()
          ↓ (depends on: UndoLog, Executor — list undo logs, let user pick one)

Step 12 ── Menu layer + main()
          Wire all ops to numbered menu items
          ↓ (depends on: all ops, DriveDetector)
```

### Why this order

- Steps 1-5 give you a working, testable core with zero business logic. You can verify
  the undo cycle before writing any organization rules.
- Step 7 (TSV rename) comes before series/movies because it's the most immediately useful
  feature and exercises the full Executor + UndoLog path with the simplest logic.
- Coherence check (step 9) is read-only and can be written before or after the mutating ops
  without affecting anything — it has no side effects.
- Menu layer last: each op can be invoked directly by calling `op_*()` with a hardcoded
  Executor during development. The menu is just a dispatcher.

---

## File Layout Within the Single .py File

```python
#!/usr/bin/env python3
# organizador.py
"""..."""

# ── 1. IMPORTS ────────────────────────────────────────────────────────────────
import os, sys, json, shutil, logging, re, csv
from pathlib import Path
from datetime import datetime
from typing import NamedTuple

# ── 2. CONFIG / CONSTANTS ─────────────────────────────────────────────────────
NO_TOUCH_EXTS = frozenset({...})
...

# ── 3. TYPES / DATA CLASSES ───────────────────────────────────────────────────
class DriveInfo(NamedTuple): ...
class FileCandidate(NamedTuple): ...

# ── 4. LOGGER SETUP ───────────────────────────────────────────────────────────
def setup_logger(log_dir: Path) -> logging.Logger: ...
logger: logging.Logger  # assigned at startup in main()

# ── 5. SAFETY GUARDS ──────────────────────────────────────────────────────────
def is_no_touch(path: Path) -> bool: ...
def is_protected_path(path: Path) -> bool: ...

# ── 6. DRIVE DETECTOR ─────────────────────────────────────────────────────────
def detect_removable_drives() -> list[DriveInfo]: ...

# ── 7. UNDO LOG ───────────────────────────────────────────────────────────────
class UndoLog: ...

# ── 8. EXECUTOR ───────────────────────────────────────────────────────────────
class Executor: ...

# ── 9. SCANNER / CLASSIFIERS ──────────────────────────────────────────────────
def scan_drive(root: Path) -> dict: ...
def parse_series_name(stem: str) -> ...: ...
def parse_movie_name(stem: str) -> ...: ...

# ── 10. OPERATIONS ────────────────────────────────────────────────────────────
def op_rename_from_tsv(root: Path, executor: Executor) -> None: ...
def op_organize_series(root: Path, executor: Executor) -> None: ...
def op_organize_movies(root: Path, executor: Executor) -> None: ...
def op_organize_games(root: Path, executor: Executor) -> None: ...
def op_cleanup_empty_dirs(root: Path, executor: Executor) -> None: ...
def op_coherence_check(root: Path) -> None: ...
def op_generate_tsv(root: Path) -> None: ...
def op_undo(root: Path) -> None: ...

# ── 11. MENU / UI ─────────────────────────────────────────────────────────────
def main_menu(root: Path) -> None: ...
def ask_dry_run() -> bool: ...
def pick_drive(drives: list[DriveInfo]) -> DriveInfo: ...

# ── 12. ENTRY POINT ───────────────────────────────────────────────────────────
def main() -> None: ...

if __name__ == "__main__":
    main()
```

This ordering matches the build order above — each section can be read and developed
independently without scrolling past things it doesn't depend on.

---

## Sources

- Ordenar.ps1 (existing PowerShell implementation — primary reference for rules and safety guards)
- PROJECT.md (requirements and constraints)
- Python stdlib docs: pathlib, shutil, logging, json (HIGH confidence — stdlib, no external deps)
- "Replace Rename Pattern" / "Command" GoF pattern — Executor as command dispatcher (HIGH confidence)
- Python atomicity: `Path.rename()` is atomic on POSIX and on Windows when on same volume (HIGH confidence, confirmed in CPython docs and Win32 MoveFileEx semantics)

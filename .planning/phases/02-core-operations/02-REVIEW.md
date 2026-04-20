---
phase: 02-core-operations
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - organizer.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-19
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

`organizer.py` is a solid single-file script that correctly applies the project's safety model (NO_TOUCH_EXTS, SKIP_PATH_PARTS) at the single mutation point in `Executor.move`. The Phase 1 infrastructure (drive detection, logging, executor) is correct. Phase 2 adds `apply_renames`, `_scan_videos_recursive`/`_walk`, `_organize_games`, `_move_subtitles`, `organize_videos_and_games`, `_remove_empty_dirs`, and the menu.

Two critical issues were found: a missing `csv` import that causes an immediate crash on menu option 2, and a path traversal vulnerability in `apply_renames` that allows a TSV file to move files anywhere on the system. Five warnings cover recursion depth limits, incorrect error classification for blocked ROM moves, a misleading early-exit message, an unbounded loop, and a TOCTOU race in path deconfliction.

---

## Critical Issues

### CR-01: Missing `csv` import — `apply_renames` crashes at runtime

**File:** `organizer.py:260`
**Issue:** `csv.DictReader` is called in `apply_renames` but `csv` is never imported. The import block at lines 3-12 lists `ctypes`, `json`, `logging`, `os`, `re`, `shutil`, `sys`, `RotatingFileHandler`, and `pathlib.Path` — `csv` is absent. Invoking menu option 2 raises `NameError: name 'csv' is not defined` immediately, before any file is read.
**Fix:**
```python
# In SECTION 1, add csv to the import block:
import csv
import ctypes
import json
import logging
import os
import re
import shutil
import sys
```

---

### CR-02: Path traversal in `apply_renames` — TSV can move files outside the drive

**File:** `organizer.py:276-284`
**Issue:** `old_path` and `new_path` values read from the user-supplied `rename_plan.tsv` are passed directly to `Path()` and then to `executor.move()` without any check that they reside within `drive_root`. `Executor.move` only blocks ROM extensions and a short list of hardcoded Windows system directories (`SKIP_PATH_PARTS`). A TSV row such as:

```
old_path	new_path
C:\Users\user\Documents\secret.docx	E:\secret.docx
```

would pass all guards and move a file from outside the removable drive. Similarly, an absolute `new_path` pointing anywhere on the filesystem is accepted.

The fix requires two containment checks — one for the source and one for the destination:

```python
src = Path(old_str)
dst = Path(new_str)

# Resolve to absolute paths and verify containment within drive_root.
# Use Path.is_relative_to() (Python 3.9+) or the parents check below.
try:
    src_resolved = src.resolve()
    dst_resolved = dst.resolve()
except OSError:
    logger.warning("Fila %d ignorada: ruta no resoluble.", i)
    counts["errores"] += 1
    continue

drive_resolved = drive_root.resolve()

if drive_resolved not in src_resolved.parents and src_resolved != drive_resolved:
    logger.warning("SKIP (ruta fuera de la unidad): %s", src)
    counts["saltados"] += 1
    continue

if drive_resolved not in dst_resolved.parents and dst_resolved != drive_resolved:
    logger.warning("SKIP (destino fuera de la unidad): %s", dst)
    counts["saltados"] += 1
    continue
```

Note: `Path.resolve()` on a non-existent path still resolves the absolute path on Python 3.6+. If the source does not yet exist, `src.resolve()` returns the absolute path without following symlinks for missing components, which is safe for this check.

---

## Warnings

### WR-01: ROM/blocked files in console folders counted as errors, not as skipped

**File:** `organizer.py:370-375`
**Issue:** `_organize_games` iterates the contents of `drive_root/PS1/`, `drive_root/GBA/`, etc. and calls `executor.move()` for every entry. When `executor.move` blocks a file due to `is_no_touch()` (e.g., a `.gba` ROM or a `.iso` image), it returns `None`. The caller counts all `None` returns as `counts["errores"]`. For a ROM-only folder this means every file is reported as an error, misleading the user into thinking the operation failed when it was intentionally blocked.
**Fix:** Add a dedicated skip counter path, or check `is_no_touch` before calling `executor.move` and increment `saltados` instead:

```python
for entry in it:
    counts["procesados"] += 1
    p = Path(entry.path)
    if is_no_touch(str(p)):
        logger.info("SKIP (no-touch ext): %s", p)
        counts["saltados"] += 1
        continue
    result = executor.move(p, dst_dir / entry.name)
    if result is not None:
        counts["movidos"] += 1
    else:
        counts["errores"] += 1
```

---

### WR-02: Unbounded recursion in `_walk` and `_remove_empty_dirs` — stack overflow on deep trees

**File:** `organizer.py:306-321`, `organizer.py:326-349`
**Issue:** Both `_walk` and `_remove_empty_dirs` use Python recursion with no depth limit. Python's default recursion limit is 1000 frames. A removable drive containing a deeply nested folder structure (e.g., a git repository or a backup with many levels) can trigger `RecursionError`, crashing the script mid-operation. This is particularly dangerous in `_remove_empty_dirs` because a crash part-way through leaves the drive in an unknown state.
**Fix (minimal):** Add an explicit depth guard parameter:

```python
def _walk(drive_root, current, exclude_roots, acc, depth=0):
    if depth > 200:
        logger.warning("SKIP (estructura demasiado profunda): %s", current)
        return
    # ... existing logic ...
    _walk(drive_root, Path(entry.path), exclude_roots, acc, depth + 1)
```

Apply the same guard to `_remove_empty_dirs`. 200 levels is a practical ceiling well below the default recursion limit.

---

### WR-03: Misleading "no video files" message when games were already organized

**File:** `organizer.py:416-418`
**Issue:** `organize_videos_and_games` runs `_organize_games` first (line 411), then scans for video files. If no video files exist but games were moved, the early return at line 417 prints "No se encontraron archivos de video para organizar." — which is technically true but confusing to a user who just saw their game files move. The returned `counts` dict does reflect the game moves, but the print implies nothing happened.
**Fix:** Print a more specific message, and only print it when the game step also produced zero moves:

```python
if not video_files:
    if counts["movidos"] == 0:
        print("No se encontraron archivos de video ni juegos para organizar.")
    else:
        print("No se encontraron archivos de video para organizar.")
    return counts
```

---

### WR-04: `_free_path` has no upper bound on the deconfliction counter

**File:** `organizer.py:127-132`
**Issue:** The `while True` loop increments `counter` without limit. In an adversarial or corrupted directory with thousands of files named `stem (N).ext`, this loops until memory is exhausted or the process is killed. While highly unlikely on a removable media drive, the absence of a bound makes the function impossible to reason about.
**Fix:** Add a hard ceiling:

```python
MAX_DECONFLICT = 9999
while counter <= MAX_DECONFLICT:
    candidate = parent / f"{stem} ({counter}){suffix}"
    if not candidate.exists():
        return candidate
    counter += 1
logger.error("No se encontro nombre libre para: %s (limite %d alcanzado)", dst, MAX_DECONFLICT)
return dst  # caller will get OSError on write — acceptable failure mode
```

---

### WR-05: `_free_path` uses `dst.exists()` which follows symlinks — inconsistent with `_walk`

**File:** `organizer.py:121`
**Issue:** `_walk` correctly uses `entry.is_dir(follow_symlinks=False)` and `entry.is_file(follow_symlinks=False)` to avoid following symlinks into unexpected locations. However `_free_path` uses `dst.exists()` and `candidate.exists()`, both of which follow symlinks by default. If the destination directory contains a dangling symlink with the same name as the target file, `exists()` returns `False` (dangling symlink target is missing) and the function returns the name without a suffix — then `shutil.move` writes to or through the symlink. More concretely: a symlink that resolves outside the drive bypasses the containment provided by the path checks.
**Fix:** Use `dst.is_symlink() or dst.exists()` as the collision check:

```python
def _path_exists_or_symlink(p: Path) -> bool:
    """True if the path exists or is a symlink (even dangling)."""
    return p.is_symlink() or p.exists()

def _free_path(dst: Path) -> Path:
    if not _path_exists_or_symlink(dst):
        return dst
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not _path_exists_or_symlink(candidate):
            return candidate
        counter += 1
```

---

## Info

### IN-01: `main()` locally shadows the module-level `logger` name

**File:** `organizer.py:499`
**Issue:** `logger = setup_console_logging()` at line 499 assigns to a local variable named `logger` inside `main()`, which shadows the module-level `logger = logging.getLogger("organizer")` at line 58. Both names resolve to the same object (since `setup_console_logging` calls `logging.getLogger("organizer")`), so there is no functional bug — but the shadowing is confusing and will trigger linters.
**Fix:** Either drop the local assignment (the module-level logger is already configured by the call) or rename the local:

```python
def main() -> None:
    setup_console_logging()          # configures module-level logger as side-effect
    drive = select_drive(get_removable_drives())
    add_file_logging(logger, Path(drive["root"]) / LOG_DIR_NAME)
    executor = Executor(dry_run=False)
    show_menu(executor, drive)
```

---

### IN-02: `show_menu` docstring references incorrect decision codes

**File:** `organizer.py:466`
**Issue:** The docstring says `"Option 5 toggles dry-run (D-01). No confirmation on operation with dry-run (D-02)."` — but D-01, D-02, D-03 are the drive-selection decisions documented in the Phase 1 section (`select_drive`). These are different decisions from the Phase 2 menu requirements and the wrong labels will cause confusion when tracing requirements.
**Fix:** Update the docstring to reference the correct Phase 2 requirement codes (or remove the decision codes if they are not yet assigned):

```python
def show_menu(executor: Executor, drive: dict) -> None:
    """Numbered main menu. Option 5 toggles dry-run mode. Options 3-4 are Phase 3/4 stubs."""
```

---

### IN-03: `_organize_games` does not recurse into console subdirectories

**File:** `organizer.py:368-375`
**Issue:** `os.scandir(src_dir)` only lists the immediate children of `drive_root/PS1/` etc. If a user has organized ROMs into subdirectories (e.g., `PS1/RPG/game.bin`, `PS1/Action/game.bin`), those subdirectories are moved as a whole unit (the directory entry itself is passed to `executor.move`). Moving a directory with `shutil.move` works, but the `is_no_touch` check operates on the directory path string — a directory named `RPG` has no extension and passes the check, so directories are moved. This is probably the intended behavior (move-directory-as-unit), but it is undocumented and differs from how individual files are handled. If the intent is to flatten all ROM files into `Juegos/PS1/`, a recursive scan is needed instead.
**Fix (documentation only, if move-directory-as-unit is intentional):** Add a comment:

```python
# Moves immediate children of src_dir. Directories are moved as a unit
# (shutil.move handles directory moves). Individual ROMs inside subdirs
# are not flattened — the subdirectory tree is preserved under Juegos/<sys>/.
```

---

_Reviewed: 2026-04-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

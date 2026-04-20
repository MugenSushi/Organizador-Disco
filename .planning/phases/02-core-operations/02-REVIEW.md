---
phase: 02-core-operations
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - organizer.py
  - verify_t2.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the Phase 2 additions in `organizer.py` (diff base `7a46787`): the video/game organiser
engine (`organize_videos_and_games`, `_organize_games`, `_move_subtitles`,
`_scan_videos_recursive`, `_walk`, `_remove_empty_dirs`), the TSV rename applier
(`apply_renames`), the compiled regex patterns, and the wired-up menu options 1, 2, and 5.
`verify_t2.py` is a smoke-test script; no issues found there.

The hard-block safety model (single mutation point in `Executor.move`) is correctly enforced.
The iterative stack-based walk and the bottom-up empty-dir cleanup via `os.walk(topdown=False)`
are both correct. The GAP-2 path-traversal containment in `apply_renames` is a good addition
but has a correctness gap: relative paths in the TSV are resolved against the process CWD rather
than the drive root (WR-01). Two additional warnings cover inaccurate error counting for
ROM-blocked files (WR-02) and a Python version compatibility risk (WR-03). Two info-level items
cover an unused import and a deferred stdlib import.

## Warnings

### WR-01: Relative paths in `rename_plan.tsv` resolve against CWD, not the drive root

**File:** `organizer.py:281-305`

**Issue:** `src = Path(old_str)` and `dst = Path(new_str)` are constructed from raw TSV values
without anchoring to `drive_root`. When a TSV row contains a relative path (e.g.,
`Videos\pelicula.mkv`), `src.exists()` at line 283 and `src.resolve()` at line 292 both resolve
relative to the Python process CWD — wherever the script was launched from — not the selected
drive. A user who writes relative paths in their TSV (a reasonable expectation given the tool
operates on one drive) will see all rows silently skipped (`src.exists()` returns False against
the script directory). The `is_relative_to(drive_root)` containment check on lines 298-299 does
correctly reject absolute paths pointing outside the drive, but it does not fix or flag relative
paths that resolved to the wrong location.

**Fix:** Anchor relative paths to `drive_root` before any existence check or resolution:

```python
src_raw = Path(old_str)
dst_raw = Path(new_str)
# Anchor relative paths to drive root — TSV may use either absolute or relative forms
src = src_raw if src_raw.is_absolute() else drive_root / src_raw
dst = dst_raw if dst_raw.is_absolute() else drive_root / dst_raw

if not src.exists():
    logger.warning("SKIP (no existe): %s", src)
    counts["saltados"] += 1
    continue

try:
    src_resolved = src.resolve()
    dst_resolved = dst.resolve()
except OSError:
    ...
```

---

### WR-02: ROM-blocked files in `_organize_games` are counted as errors, not as skipped

**File:** `organizer.py:396-402`

**Issue:** `_organize_games` calls `executor.move()` for every entry in each console folder and
counts a `None` return as `counts["errores"]`. `Executor.move()` returns `None` for both
genuine OS errors AND for hard-block skips (ROM/ISO extensions via `is_no_touch`). Because
console folders such as `PS1/` or `GBA/` are precisely the directories most likely to contain
files with blocked extensions (`.gba`, `.iso`, `.bin`, etc.), a normal run against a ROM drive
will report every file as an error, giving the user a misleading failure signal when the
operation was intentionally blocked.

**Fix:** Check `is_no_touch` before calling `executor.move` and route to `saltados`:

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

### WR-03: `Path.is_relative_to()` requires Python 3.9 — crashes silently on Python 3.6-3.8

**File:** `organizer.py:298-299`

**Issue:** The comment at line 290 acknowledges the 3.9+ requirement but the code uses the API
unconditionally. CLAUDE.md specifies "Python 3.x" without a floor version. On Python 3.6, 3.7,
or 3.8 (all still installed on Windows systems), reaching line 298 raises `AttributeError:
'WindowsPath' object has no attribute 'is_relative_to'`. This crashes the entire rename
operation without a user-visible error message — the exception propagates out of `apply_renames`
and up through `show_menu`, which has no try/except, terminating the script.

**Fix:** Replace `is_relative_to()` with a string prefix check that works on Python 3.6+:

```python
drive_root_str = str(drive_root.resolve()).lower()
if not str(src_resolved).lower().startswith(drive_root_str + "\\") and \
        str(src_resolved).lower() != drive_root_str:
    ...
if not str(dst_resolved).lower().startswith(drive_root_str + "\\") and \
        str(dst_resolved).lower() != drive_root_str:
    ...
```

Alternatively, add a startup version guard in `main()`:

```python
if sys.version_info < (3, 9):
    print("Este script requiere Python 3.9 o superior.")
    sys.exit(1)
```

---

## Info

### IN-01: `import json` is unused

**File:** `organizer.py:6`

**Issue:** `json` is imported at line 6 but is never referenced in the current code. The undo
log (Phase 3) will use it, but as written `json` is dead code that will be flagged by any
linter (`flake8 F401`, `pylint W0611`).

**Fix:** Remove the import for now and restore it in Phase 3 when the undo log is implemented.

---

### IN-02: `import time` is deferred inside `_free_path` function body

**File:** `organizer.py:134`

**Issue:** `import time as _time` is placed inside the function body as a fallback branch for
the 9999-collision edge case. There is no circular-import or optional-dependency reason to defer
`time` — it is stdlib. Deferred imports inside function bodies are a code smell, add minor
per-call overhead on the first hit, and deviate from CLAUDE.md's convention of listing all
imports in Section 1.

**Fix:** Move to the top-level imports block in Section 1:

```python
import time
```

And update the reference in `_free_path`:

```python
ts = int(time.time() * 1000)
return parent / f"{stem} ({ts}){suffix}"
```

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 02-core-operations
plan: "03"
subsystem: organizer-core
tags: [bugfix, security, robustness, gap-closure]
dependency_graph:
  requires: ["02-01", "02-02"]
  provides: ["GAP-1-closed", "GAP-2-closed", "GAP-3-closed", "WR-02-addressed", "WR-04-addressed"]
  affects: ["organizer.py"]
tech_stack:
  added: []
  patterns: ["Path.is_relative_to() for containment checks", "os.walk topdown=False for bottom-up dir removal", "iterative stack-based traversal"]
key_files:
  created: []
  modified: ["organizer.py"]
decisions:
  - "Use import time as _time inside _free_path fallback body to avoid adding a top-level import for a single defensive edge case"
  - "Two remaining while True loops (select_drive, show_menu) are intentional menu loops — not in scope of WR-04"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-20"
  tasks_completed: 3
  files_modified: 1
---

# Phase 02 Plan 03: Gap Closure — Three Blocker Fixes Summary

**One-liner:** Surgical fixes for csv NameError crash (GAP-1), path traversal security gap (GAP-2), and UnicodeEncodeError on cp1252 terminals (GAP-3), plus iterative refactors for _walk and _remove_empty_dirs to eliminate unbounded recursion.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix GAP-1 (csv import) and GAP-3 (UnicodeEncodeError) | f8cc107 | organizer.py |
| 2 | Fix GAP-2 (drive_root containment in apply_renames) | d275550 | organizer.py |
| 3 | Cap _free_path, convert _walk and _remove_empty_dirs to iterative | b703f83 | organizer.py |

## Gaps Fixed

### GAP-1 — Missing `import csv` (fixes RENAME-01, RENAME-02)
- **Root cause:** `apply_renames()` called `csv.DictReader` but `csv` was never imported.
- **Fix:** Inserted `import csv` alphabetically between `import ctypes` and `import json` in SECTION 1.
- **Verification:** `grep "^import csv" organizer.py` → `5:import csv`; `python -c "import organizer; print('import OK')"` exits 0.

### GAP-2 — Path traversal in apply_renames (fixes security gap T-02-GAP-01)
- **Root cause:** TSV rows with absolute paths outside the selected drive were passed directly to `executor.move()` without containment validation.
- **Fix:** Before `executor.move()`, resolve both `src` and `dst` via `.resolve()`, then check `is_relative_to(drive_root.resolve())` on both. Paths outside drive increment `saltados` and log a `SKIP (path traversal)` warning. `OSError` during resolve also safely skips the row.
- **Verification:** `grep "is_relative_to" organizer.py` → 2 matches; smoke test confirms `C:/Windows` correctly detected as outside `D:/TestDrive`.

### GAP-3 — UnicodeEncodeError on cp1252 terminals (fixes MENU-03)
- **Root cause:** `_print_summary()` used U+2713 (✓) which cp1252 cannot encode.
- **Fix:** Replaced `\u2713` with `[OK]` ASCII marker in both the print statement and the docstring.
- **Verification:** `python -c "content=open('organizer.py',encoding='utf-8').read(); assert chr(0x2713) not in content"` exits 0.

## Warnings Addressed

### WR-04 — _free_path unbounded loop
- **Fix:** Changed `while True` to `while counter <= 9999`. Added timestamp fallback (`import time as _time` inside function body) to guarantee uniqueness even when 9999 collision candidates exist.
- **Verification:** `grep "while counter <= 9999" organizer.py` → 1 match; `grep "while True" organizer.py` → only `select_drive` and `show_menu` (both intentional menu loops).

### WR-02 — Recursion depth risk in _walk and _remove_empty_dirs
- **_walk fix:** Replaced recursive implementation with iterative stack-based traversal. Signature parameter renamed from `current` to `start`; backward-compatible since all call sites use positional arguments.
- **_remove_empty_dirs fix:** Replaced recursive scandir approach with `os.walk(root, topdown=False)` which provides identical bottom-up semantics without consuming call stack. `shutil.rmtree` remains absent (ORG-05 constraint preserved).
- **Verification:** `_remove_empty_dirs smoke test: PASS` — empty dirs removed, non-empty dirs kept, root never removed.

## End-to-End Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Compile | `py -m py_compile organizer.py` | exit 0 |
| Import | `python -c "import organizer; print('import OK')"` | `import OK` |
| csv import | `grep "^import csv" organizer.py` | `5:import csv` |
| Containment | `grep "is_relative_to" organizer.py` | 2 matches |
| No U+2713 | `python -c "assert chr(0x2713) not in content"` | `No U+2713: OK` |
| [OK] marker | `grep "\[OK\]" organizer.py` | 2 matches in _print_summary |
| No unbounded loop | `grep "while True" organizer.py` | only select_drive + show_menu |
| os.walk | `grep "os.walk" organizer.py` | 1 match in _remove_empty_dirs |
| No shutil.rmtree | AST check | `PASS` |
| _remove_empty_dirs | smoke test | `PASS` |

## Deviations from Plan

None — plan executed exactly as written. All three task actions matched their specifications precisely.

## Known Stubs

None — no stub values or placeholder data introduced.

## Threat Flags

No new threat surface introduced. GAP-2 fix closes the existing T-02-GAP-01 threat (path traversal via TSV).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| organizer.py exists | FOUND |
| 02-03-SUMMARY.md exists | FOUND |
| commit f8cc107 exists | FOUND |
| commit d275550 exists | FOUND |
| commit b703f83 exists | FOUND |

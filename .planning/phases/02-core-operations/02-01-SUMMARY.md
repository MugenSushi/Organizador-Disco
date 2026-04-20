---
phase: 02-core-operations
plan: "01"
subsystem: organizer-core
tags: [constants, regex, tsv-rename, video-scanner, empty-dir-cleanup]
dependency_graph:
  requires: [01-01]
  provides: [VIDEO_EXTS, SUB_EXTS, CONSOLE_SYSTEMS, SCAN_EXCLUDE_DIR_NAMES, CLEANUP_EXCLUDE_NAMES, RE_SERIES, RE_MOVIE, apply_renames, _scan_videos_recursive, _walk, _remove_empty_dirs]
  affects: [organizer.py]
tech_stack:
  added: []
  patterns: [frozenset-constants, module-level-regex, csv-DictReader-tab, os-scandir-no-glob, Path-rmdir-bottom-up]
key_files:
  created: []
  modified: [organizer.py]
decisions:
  - "CONSOLE_SYSTEMS excludes PC and Steam per D-04 locked decision"
  - "apply_renames uses utf-8-sig encoding to handle Excel BOM in TSV files"
  - "_walk uses os.scandir exclusively — never glob/rglob — to handle bracket characters in filenames"
  - "_remove_empty_dirs uses Path.rmdir() only — shutil.rmtree forbidden by ORG-05"
metrics:
  duration: ~10m
  completed_date: "2026-04-19"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 02 Plan 01: Foundational Helpers Summary

**One-liner:** Phase 2 constants, module-level regex, TSV rename applier with utf-8-sig+tab, os.scandir video scanner, and bottom-up empty-dir cleanup added to organizer.py sections 9-12.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add constants (SECTION 2) and compiled regex (SECTION 9) | 85c1e79 | organizer.py |
| 2 | Add apply_renames (S10), _scan_videos_recursive+_walk (S11), _remove_empty_dirs (S12) | d992524 | organizer.py |

## What Was Built

### SECTION 2 Additions — Constants

Five new module-level constants appended after `DRIVE_REMOVABLE`:

- `VIDEO_EXTS: frozenset[str]` — nine video extensions for scanner filtering
- `SUB_EXTS: tuple[str, ...]` — four subtitle extensions
- `CONSOLE_SYSTEMS: tuple[str, ...]` — PS1, PS2, PSP, GBA, GBC (PC/Steam excluded per D-04)
- `SCAN_EXCLUDE_DIR_NAMES: frozenset[str]` — top-level dirs to skip during scan
- `CLEANUP_EXCLUDE_NAMES: frozenset[str]` — dirs to skip during empty-dir cleanup

### SECTION 9 — Compiled Regex

Two patterns compiled at module level (never inside functions):

- `RE_SERIES` — matches "Show - Temporada N - Episodio N" with named groups `show`, `season`, `ep`
- `RE_MOVIE` — matches "Title (YYYY)" with named groups `title`, `year`; year restricted to 19xx/20xx

Old show_menu section header renumbered from SECTION 9 to SECTION 14.

### SECTION 10 — apply_renames()

Reads `<drive>/_organizer_logs/rename_plan.tsv` using `csv.DictReader` with `delimiter="\t"` and `encoding="utf-8-sig"` (handles Excel BOM). Constructs paths with `Path(old_str)` — literal, no glob expansion. Routes each move through `executor.move()`. Returns `{procesados, movidos, saltados, errores}` counts dict.

### SECTION 11 — _scan_videos_recursive() + _walk()

`_scan_videos_recursive(root, exclude_roots)` traverses via `_walk()` using `os.scandir` exclusively. Top-level excluded dirs are skipped only when `current == drive_root`. `follow_symlinks=False` on all `is_dir()` and `is_file()` calls. `should_skip_path()` filters system paths. `PermissionError` handled with warning log, not crash.

### SECTION 12 — _remove_empty_dirs()

Bottom-up traversal: recurses into each child directory before attempting `child.rmdir()`. `CLEANUP_EXCLUDE_NAMES` dirs are skipped. `OSError` on non-empty dirs silently passed (best-effort). Never uses `shutil.rmtree`.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Coverage

All T-02-01 through T-02-05 mitigations implemented as specified:

| Threat | Mitigation Applied |
|--------|--------------------|
| T-02-01 Tampering via TSV paths | `Path()` literal construction + `executor.move()` enforces `is_no_touch()` + `should_skip_path()` |
| T-02-02 Symlink escape | `follow_symlinks=False` on all `is_dir()` and `is_file()` in `_walk()` |
| T-02-03 Path traversal (../../..) | `should_skip_path()` blocks system paths before any shutil call |
| T-02-04 DoS via deep empty dirs | `os.rmdir` raises `OSError` for non-empty; recursion bounded by filesystem depth |
| T-02-05 Info disclosure via logs | Log written to user-selected removable drive only; no network exposure |

## Known Stubs

None — all functions are fully implemented. No placeholder text or hardcoded empty returns that affect plan goal.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced beyond what the threat model covers.

## Self-Check: PASSED

- organizer.py exists and passes `py -m py_compile`
- Commits 85c1e79 and d992524 exist in git log
- All acceptance criteria verified via automated test scripts
- `Plan 01 verification PASS` confirmed

---
phase: 03-safety-features
plan: 02
subsystem: undo
tags: [undo, revert, json, path-traversal-guard, shutil]

# Dependency graph
requires:
  - phase: 03-safety-features
    plan: 01
    provides: last_run.json with serial + drive-relative moves, show_menu(drives) param, LOG_DIR_NAME
provides:
  - undo_last_run(drive, all_drives) function in SECTION 15
  - show_menu option 3 wired to undo_last_run
affects:
  - end-user: menu option 3 now reverses last organize/rename operation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - reversed(moves) for LIFO revert order
    - Serial matching across all_drives for drive-letter-change resilience (UNDO-02)
    - D-04 skip-not-error: missing dst file counted in skipped list, never aborts loop
    - Path traversal guard: src_abs and dst_abs resolved and checked against drive_root
    - Atomic log deletion via Path.unlink() with OSError silent-skip

key-files:
  created: []
  modified:
    - organizer.py

key-decisions:
  - "Serial match search iterates all_drives first; fallback to current drive path handles common case efficiently"
  - "skipped is a list (not counter) to print individual file paths after summary"
  - "log deleted even when all entries were skipped — prevents double-undo on zero-file run"
  - "src_abs.parent.mkdir(parents=True, exist_ok=True) before shutil.move — recreates original directory if it was removed after organize"

requirements-completed: [UNDO-03]

# Metrics
duration: 10min
completed: 2026-04-21
---

# Phase 3 Plan 02: Undo Revert UI Summary

**undo_last_run() reads last_run.json, re-anchors by serial for drive-letter resilience, reverts all moves in reverse order skipping missing files, and deletes the log after to prevent double-undo**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-21
- **Completed:** 2026-04-21
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `undo_last_run(drive, all_drives)` to SECTION 15 of organizer.py (after `_flush_and_clear`, before `show_menu`)
- Function searches all drives by volume serial before falling back to current drive path (UNDO-02 drive-letter-change resilience)
- Revert loop iterates `reversed(moves)`, calling `shutil.move(str(dst_abs), str(src_abs))` for each entry
- Missing dst files counted in `skipped` list (not `errors`), loop never aborts (D-04)
- Path traversal guard mirrors `apply_renames()` pattern exactly — both src_abs and dst_abs resolved and checked against `drive_root_str`
- Summary line: `[OK] Revertidos: N | Saltados: N | Errores: N` (ASCII [OK], no unicode)
- Skipped file paths printed after summary when list is non-empty
- `last_run.json` deleted after undo via `Path.unlink()` with `OSError: pass` (prevents double-undo, T-03-06)
- Replaced show_menu option 3 stub `print("(Disponible en Fase 3)")` with `undo_last_run(drive, drives)`

## Task Commits

1. **Task 1: Implement undo_last_run() and wire to menu option 3** - `6cdba6c` (feat)

## Files Created/Modified

- `organizer.py` - Added `undo_last_run()` (110 lines) to SECTION 15; replaced option 3 stub in show_menu

## Decisions Made

- Serial match iterates `all_drives` first with `fallback` path for current drive — handles both the drive-letter-changed case and the common unchanged-letter case without redundant work
- `skipped` stored as list (not int counter) so individual file paths can be printed after the summary line
- Log deleted even when all entries were skipped (zero reverted) — any completed undo attempt clears the log to prevent a second undo from appearing to succeed on a stale log
- `src_abs.parent.mkdir(parents=True, exist_ok=True)` before `shutil.move` — recreates the original directory tree if it was cleaned up by `_remove_empty_dirs` after an organize operation

## Deviations from Plan

None - plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-03-04 | Both src_abs and dst_abs resolved and checked with startswith(drive_root_str + "\\") before any move; logged as warning, counted as skipped |
| T-03-05 | entry.get("src", "") with empty-string check; json.JSONDecodeError caught on load; malformed entries skipped with warning |
| T-03-06 | last_run.json deleted after undo; second call hits "No hay ninguna operacion" early return |
| T-03-07 | Path traversal guard mirrors apply_renames() pattern, verified in Phase 2 |

## Known Stubs

None - undo_last_run is fully implemented and wired.

## Self-Check: PASSED

- `organizer.py` exists and imports cleanly
- `def undo_last_run` present at line 566
- `undo_last_run(drive, drives)` call site present at line 703
- "Disponible en Fase 3" stub fully removed
- Commit `6cdba6c` exists
- All 4 automated verify assertions print PASS

---
*Phase: 03-safety-features*
*Completed: 2026-04-21*

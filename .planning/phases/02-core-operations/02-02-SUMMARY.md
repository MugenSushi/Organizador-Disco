---
phase: 02-core-operations
plan: "02"
subsystem: organizer-core
tags: [organize-videos, organize-games, subtitle-colocation, dry-run-toggle, menu-wiring]
dependency_graph:
  requires: [02-01]
  provides: [_organize_games, _move_subtitles, organize_videos_and_games, _print_summary, show_menu-wired]
  affects: [organizer.py]
tech_stack:
  added: []
  patterns: [os-scandir-contents-not-folder, result.parent-for-subtitle-dst, u2713-escape-cp1252-safe]
key_files:
  created: []
  modified: [organizer.py]
decisions:
  - "D-01: dry-run label computed fresh each loop iteration from executor.dry_run — always current"
  - "D-02: no confirmation prompt between option selection and execution even in dry-run mode"
  - "D-03: executor.dry_run flipped via attribute assignment; Executor not reconstructed"
  - "_move_subtitles uses result.parent (actual collision-resolved path) not dst_dir — correct when _free_path applies suffix"
  - "U+2713 checkmark written as \\u2713 escape in source — avoids UnicodeEncodeError on Windows cp1252 console"
metrics:
  duration: ~8m
  completed_date: "2026-04-19"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 02 Plan 02: Wire Organize Engine into Menu Summary

**One-liner:** SECTION 13 game+video+subtitle organizer inserted and wired into show_menu() with option 5 dry-run toggle and U+2713 one-line summary output.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add SECTION 13 — _organize_games, _move_subtitles, organize_videos_and_games | b30344e | organizer.py |
| 2 | Update show_menu() with option 5 dry-run toggle, wire options 1-2, add _print_summary() | 3afb250 | organizer.py |

## What Was Built

### SECTION 13 — File Organization Operations

Three new functions inserted between SECTION 12 (`_remove_empty_dirs`) and SECTION 14 (`show_menu`):

**`_organize_games(executor, drive_root, counts)`**
- Iterates `CONSOLE_SYSTEMS` (PS1, PS2, PSP, GBA, GBC)
- For each system folder that exists, uses `os.scandir(src_dir)` to iterate contents
- Moves each `entry.path` to `Juegos/<system>/<entry.name>` — moves contents, not the folder itself (avoids Pitfall 2: `Juegos/PS1/PS1/` double-nesting)
- `PermissionError` handled with warning log, not crash

**`_move_subtitles(executor, video_src, video_dst_dir, counts)`**
- Checks `video_src.parent` for each extension in `SUB_EXTS` (.srt/.ass/.sub/.idx) matching `video_src.stem`
- Moves matching subtitle files to `video_dst_dir` (the actual collision-resolved parent of the moved video)
- Only callable when video move succeeded (caller enforces `result is not None` guard — Pitfall 3)

**`organize_videos_and_games(executor, drive_root)`**
- Step 1: `_organize_games()` — game folder contents
- Step 2: `_scan_videos_recursive()` — find all video files excluding already-organized dirs
- Step 3: classify each video as series (`RE_SERIES`) or movie (`RE_MOVIE`) or unmatched (goes to Peliculas/<stem>/)
- Step 4: `executor.move()` + `_move_subtitles(executor, video_path, result.parent, counts)` on success
- Step 5: `_remove_empty_dirs()` after all moves complete
- Returns `{procesados, movidos, saltados, errores}` counter dict

### SECTION 14 Updates

**`_print_summary(counts)`** — added immediately before `show_menu()`:
- Outputs single `print()` line (not `logger` — user-visible output per MENU-03)
- Format: `✓ Procesados: N | Movidos: N | Saltados: N | Errores: N`
- Checkmark written as `\u2713` escape — safe on Windows cp1252 console (avoids UnicodeEncodeError, Pitfall 8)

**`show_menu(executor, drive)`** — full replacement of Phase 1 stub version:
- Option 1: `counts = organize_videos_and_games(executor, Path(drive["root"]))` + `_print_summary(counts)`
- Option 2: `counts = apply_renames(executor, Path(drive["root"]))` + `_print_summary(counts)`
- Option 3/4: Phase 3/4 stubs unchanged
- Option 5: `executor.dry_run = not executor.dry_run` — in-place flip, label reads fresh each loop iteration
- Phase 2 stubs `"(Disponible en Fase 2)"` removed

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Coverage

All T-02-06 through T-02-10 mitigations implemented as specified:

| Threat | Mitigation Applied |
|--------|--------------------|
| T-02-06 Tampering via video moves | All moves via `Executor.move()` which enforces `is_no_touch()` + `should_skip_path()` |
| T-02-07 Tampering via game folder moves | `CONSOLE_SYSTEMS` hardcoded constant; no user input influences folder scan; Executor enforces hard blocks |
| T-02-08 Tampering via subtitle moves | Only called when `result is not None`; uses `video_src.stem` from scanned path, not user input |
| T-02-09 DoS double-move on re-run | `SCAN_EXCLUDE_DIR_NAMES` excludes "series", "peliculas", "juegos" at drive root level |
| T-02-10 Spoofing menu choice | Input used only as branch selector; invalid input loops with "Opcion invalida." |

## Known Stubs

None — all Phase 2 functions are fully implemented. Options 1, 2, and 5 are wired. Options 3 and 4 retain intentional Phase 3/4 stubs; these are forward-compatibility placeholders, not plan goals.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond what the threat model covers.

## Self-Check: PASSED

- organizer.py exists (510 lines, above 430 minimum) and passes `py -m py_compile`
- Commits b30344e and 3afb250 exist in git log
- All 8 Phase 2 functions callable: apply_renames, _scan_videos_recursive, _walk, _remove_empty_dirs, _organize_games, _move_subtitles, organize_videos_and_games, _print_summary
- `Phase 2 Plan 02 verification PASS` confirmed via automated test script
- No accidental file deletions in either commit

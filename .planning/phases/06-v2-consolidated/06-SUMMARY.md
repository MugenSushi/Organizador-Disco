# Phase 6 Summary: v2 — Consolidated "Ordenar Todo"

**Phase:** 06-v2-consolidated
**Status:** complete
**Completed:** 2026-04-22

## What Was Built

Added `organize_all()` function that runs all organization operations in a single menu option:
1. `organize_videos_and_games()` — videos (Series/Películas), console games (Juegos), subtitles
2. `organize_other_files()` — documents (DOCS), PC games (Juegos PC), software (Software)
3. `_remove_empty_dirs()` — cleanup of resulting empty folders

## What Changed

### Menu Structure (Before → After)

**Before (7 options + exit):**
1. Organizar videos y juegos
2. Organizar documentos, juegos PC y software
3. Aplicar rename_plan.tsv
4. Revertir ultima operacion
5. Detectar incoherencias
6. Dry-run toggle
7. Generar rename_plan.tsv
0. Salir

**After (6 options + exit):**
1. Ordenar todo
2. Aplicar rename_plan.tsv
3. Revertir ultima operacion
4. Detectar incoherencias
5. Dry-run toggle
6. Generar rename_plan.tsv
0. Salir

### Files Modified

- `organizer.py` — Added `organize_all()`, updated `show_menu()`
- `.planning/REQUIREMENTS.md` — V2-05, V2-06 marked complete
- `.planning/ROADMAP.md` — Phase 6 marked complete
- `.planning/STATE.md` — milestone updated to v2.0

## Verification

- `organize_all()` function exists and calls all 3 operations in sequence
- Menu displays "Ordenar todo" as option 1
- Selecting "1" runs `organize_all()` with proper executor setup and undo logging
- V2-05 and V2-06 requirements marked complete in REQUIREMENTS.md

## Decisions

1. **organize_all returns merged counts** — combines counters from both organization passes so user sees total processed/moved/skipped/errors
2. **_remove_empty_dirs called with empty list** — intentionally discards removed folder list since this is a cleanup pass, not a tracked operation
3. **Undo log captures all moves** — since both organize_videos_and_games and organize_other_files route through the same executor, all moves are accumulated and written to undo log atomically
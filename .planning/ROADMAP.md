# Roadmap: Organizador de Disco

## Overview

Four phases build from a safe, tested foundation to a fully operational organizer.
Phase 1 constructs the skeleton: drive detection, safety guards, dry-run executor, and undo log.
Phase 2 wires in all file operations: renames, series/movies/games organization, subtitle co-location, and empty-folder cleanup.
Phase 3 surfaces the safety net to the user: undo/rollback UI and run summaries.
Phase 4 adds analytical power: TSV rename plan generator and coherence checker.
Phases 1+2 already replace both PowerShell scripts. Phases 3+4 make it safer and smarter.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure** - Drive detection, safety guards, Executor, UndoLog, Scanner, and menu shell
- [ ] **Phase 2: Core Operations** - All file-moving operations: renames, organize series/movies/games, subtitle co-location, empty-folder cleanup
- [ ] **Phase 3: Safety Features** - Undo/rollback UI, dry-run preview, operation summaries wired to the menu
- [ ] **Phase 4: Power Features** - TSV rename plan generator and coherence checker
- [x] **Phase 7: v2.1 — Series Sin Subcarpetas de Temporada** - All episodes of a series in one folder, no Temporada subfolders

### Phase 6: v2 — Consolidated "Ordenar Todo"
**Goal**: Single menu option that organizes everything (videos, games, other files) and cleans empty folders in one pass.
**Depends on**: Phase 1, Phase 5
**Success Criteria** (what must be TRUE):
1. A single "Ordenar todo" option runs organize_videos_and_games, organize_other_files, and empty folder cleanup in sequence
2. After organizing, all resulting empty folders are removed
3. All existing safety features (dry-run, undo, hard blocks) work identically for the consolidated operation
4. The menu is simplified: only "Ordenar todo", apply renames, undo, coherence, dry-run toggle, generate rename plan, and exit remain
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md — Consolidate menu: merge options 1+2 into "Ordenar todo", remove separate file organizer option

### Phase 7: v2.1 — Series Sin Subcarpetas de Temporada
**Goal**: All episodes of a series are placed directly in `Series\<Show>\` without Temporada subfolders.
**Depends on**: Phase 6
**Success Criteria** (what must be TRUE):
1. Series files matching the pattern are moved to `Series\<Show>\episode.mp4` (no Temporada X subfolder)
2. Movies continue to use `Peliculas\<Titulo (Ano)>\` unchanged
3. Undo log correctly records the new paths
**Plans**: 1 plan

Plans:
- [x] 07-01-PLAN.md — Modify organize_videos_and_games: remove Temporada subfolder creation for series

## Phase Details

### Phase 1: Infrastructure
**Goal**: The script boots, selects a drive, and can safely describe any future operation without touching the filesystem
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, MENU-01
**Success Criteria** (what must be TRUE):
  1. Running the script on Windows lists all removable drives and asks the user to pick one; invalid input is rejected
  2. Any path containing a ROM/ISO extension or a protected system folder is blocked at the Executor level and never moved
  3. The Executor's dry_run flag causes every move/rename to print what would happen instead of changing anything on disk
  4. Calling Executor.move() with a destination that already exists produces a collision-safe target path (suffix 2, 3...) rather than overwriting
  5. A numbered main menu is presented after drive selection; the script does not require any command-line arguments
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Create organizer.py: constants, safety guards, Executor class, logging, drive selection UI, and main menu shell

### Phase 2: Core Operations
**Goal**: Users can fully organize a drive — applying renames, sorting series/movies/games, co-locating subtitles, and removing empty folders
**Depends on**: Phase 1
**Requirements**: RENAME-01, RENAME-02, ORG-01, ORG-02, ORG-03, ORG-04, ORG-05, MENU-02, MENU-03
**Success Criteria** (what must be TRUE):
  1. Loading a valid rename_plan.tsv and choosing "Apply renames" moves (or dry-run reports) every listed file using literal paths; bracket characters in filenames are handled correctly
  2. Choosing "Organize" detects series files by pattern and places them under Series\<Show>\Temporada X\
  3. Choosing "Organize" detects movie files by pattern and places them under Peliculas\<Titulo (Ano)>\
  4. Game system folders (PS1, PS2, PSP, GBA, GBC) are moved into Juegos\<system>\ (PC and Steam excluded per D-04)
  5. After any organize operation, subtitle files (.srt .ass .sub .idx) sharing a basename with a moved video land beside that video, and all resulting empty folders are removed with os.rmdir
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Add Phase 2 engine: constants, compiled regex patterns, apply_renames(), _scan_videos_recursive(), _remove_empty_dirs()
- [x] 02-02-PLAN.md — Wire organize operations: _organize_games(), organize_videos_and_games(), update show_menu() with option 5 and _print_summary()

### Phase 3: Safety Features
**Goal**: Users can confidently undo any operation and see a plain-language summary of what just happened
**Depends on**: Phase 2
**Requirements**: UNDO-01, UNDO-02, UNDO-03
**Success Criteria** (what must be TRUE):
  1. After any operation that moves or renames files, a JSON log is written atomically to <drive>\_organizer_logs\ recording every change with drive-relative paths and volume serial number
  2. Selecting "Undo last run" from the menu reverses every move from the most recent log in correct reverse order, and the log is resolved to the correct drive even if its letter changed since the last run
  3. At the end of every operation the menu displays a summary line: files processed, moved, skipped, and errors
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Executor accumulator, flush_undo_log(), _prepare_executor_for_run(), _flush_and_clear(), show_menu/main wiring
- [x] 03-02-PLAN.md — undo_last_run() with serial re-anchoring, path traversal guard, reverse revert; wire menu option 3

### Phase 4: Power Features
**Goal**: Users can discover rename candidates automatically and audit the drive for structural problems without manual inspection
**Depends on**: Phase 3
**Requirements**: RENAME-03, RENAME-04, COH-01, COH-02, COH-03
**Success Criteria** (what must be TRUE):
  1. Selecting "Generate rename plan" scans the drive and writes a rename_plan.tsv to _organizer_logs\ — the file is never auto-applied; the user must manually trigger "Apply renames" separately
  2. The coherence report lists video files found outside Series\ and Peliculas\ that match a known series or movie pattern
  3. The coherence report flags series episodes present without a Temporada X subfolder
  4. The coherence report identifies title duplicates after normalizing names (stripping year, resolution tags, etc.)
**Plans**: TBD

### Phase 5: General File Organizer
**Goal**: Users can organize the rest of the hard drive (documents, PC games, and software) securely with the same dry-run and undo guarantees.
**Depends on**: Phase 1, Phase 3
**Requirements**: ORG-06, ORG-07, ORG-08
**Success Criteria** (what must be TRUE):
  1. Loose documents with known extensions (PDF, HTML, TXT, CSV, etc.) are moved to DOCS\
  2. Known game launchers and PC games folders are moved to Juegos PC\
  3. Known music production software folders are moved to Software\
  4. Other console game folders (like Juegos PS1) remain untouched.
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — Add `organize_other_files` and wire to a new menu option.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 1/1 | Completed | 2026-04-22 |
| 2. Core Operations | 2/2 | Completed | 2026-04-22 |
| 3. Safety Features | 2/2 | Completed | 2026-04-22 |
| 4. Power Features | 1/1 | Completed | 2026-04-22 |
| 5. General File Organizer | 1/1 | Completed | 2026-04-22 |
| 6. v2 Consolidated | 1/1 | Completed | 2026-04-22 |
| 7. v2.1 Series Flat | 1/1 | Completed | 2026-04-22 |



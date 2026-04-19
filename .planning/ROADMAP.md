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
**Plans**: TBD

### Phase 2: Core Operations
**Goal**: Users can fully organize a drive — applying renames, sorting series/movies/games, co-locating subtitles, and removing empty folders
**Depends on**: Phase 1
**Requirements**: RENAME-01, RENAME-02, ORG-01, ORG-02, ORG-03, ORG-04, ORG-05, MENU-02, MENU-03
**Success Criteria** (what must be TRUE):
  1. Loading a valid rename_plan.tsv and choosing "Apply renames" moves (or dry-run reports) every listed file using literal paths; bracket characters in filenames are handled correctly
  2. Choosing "Organize" detects series files by pattern and places them under Series\<Show>\Temporada X\
  3. Choosing "Organize" detects movie files by pattern and places them under Peliculas\<Titulo (Año)>\
  4. Game system folders (PC, PS1, PS2, PSP, GBA, GBC) are moved into Juegos\<system>\
  5. After any organize operation, subtitle files (.srt .ass .sub .idx) sharing a basename with a moved video land beside that video, and all resulting empty folders are removed with os.rmdir
**Plans**: TBD
**UI hint**: yes

### Phase 3: Safety Features
**Goal**: Users can confidently undo any operation and see a plain-language summary of what just happened
**Depends on**: Phase 2
**Requirements**: UNDO-01, UNDO-02, UNDO-03
**Success Criteria** (what must be TRUE):
  1. After any operation that moves or renames files, a JSON log is written atomically to <drive>\_organizer_logs\ recording every change with drive-relative paths and volume serial number
  2. Selecting "Undo last run" from the menu reverses every move from the most recent log in correct reverse order, and the log is resolved to the correct drive even if its letter changed since the last run
  3. At the end of every operation the menu displays a summary line: files processed, moved, skipped, and errors
**Plans**: TBD

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

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 0/TBD | Not started | - |
| 2. Core Operations | 0/TBD | Not started | - |
| 3. Safety Features | 0/TBD | Not started | - |
| 4. Power Features | 0/TBD | Not started | - |

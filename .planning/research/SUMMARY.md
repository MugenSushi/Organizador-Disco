# Research Summary: Python Media File Organizer CLI

**Overall Confidence:** HIGH — grounded in official Python 3 docs and direct analysis of existing PowerShell scripts.

---

## Executive Summary

Windows-only, single-file Python CLI that replaces two PowerShell scripts. Organizes video series, movies, and game folders on a removable drive. Interactive numbered menu, zero external dependencies (stdlib only), single user running it occasionally on one drive at a time.

Key architectural decision: **Executor pattern** — all filesystem mutations route through one object holding the dry-run flag. Every operation is preview-capable without scattered conditionals.

The dominant risks are data-integrity issues: silent file skipping due to glob bracket metacharacters, non-atomic cross-drive moves, and stale undo logs when drive letter changes on reconnect.

---

## 1. Recommended Stack

| Module | Role |
|--------|------|
| `pathlib.Path` | All path construction, existence checks, extension access |
| `shutil` | File moves — `shutil.move()` only, NEVER `Path.rename()` across dirs |
| `os` | Atomic write (`os.replace`), `os.scandir()` for file discovery — NOT glob |
| `ctypes.windll` | Removable drive detection via `GetDriveTypeW` (returns `2` for DRIVE_REMOVABLE) |
| `json` | Undo log — write full array atomically, never append line-by-line |
| `csv` | TSV reader — `DictReader(delimiter='\t')` with `encoding="utf-8-sig"` for BOM |
| `re` | Filename pattern matching — compile at module level, named groups |
| `logging` | Dual output (file + console) — named logger + explicit handlers |
| `input()` / `print()` | Interactive menu — NO curses (broken on Windows without non-stdlib) |

---

## 2. Table Stakes Features (Must-Have)

1. Removable drive detection and selection
2. Organize series → `Series\<Show>\Temporada X\`
3. Organize movies → `Peliculas\<Title (Year)>\`
4. Organize games → `Juegos\<System>\` (PC, PS1, PS2, PSP, GBA, GBC)
5. Co-locate subtitles (.srt .ass .sub .idx) with matching video by basename
6. Hard ROM/ISO protection — `is_no_touch()` at every path-touching site
7. Collision-safe destinations — `(2)`, `(3)` suffix via `_free_path()` before every move
8. Dry-run mode — structured preview with counts
9. Undo/rollback — JSON log written atomically
10. Empty folder cleanup after moves — `os.rmdir()` only, never `shutil.rmtree()`
11. Persistent run log to `<drive>\_organizer_logs\`
12. Apply renames from `rename_plan.tsv`

Deferred: TSV rename plan generator, coherence checker.

---

## 3. Architecture (Single .py File Structure)

```
 1. IMPORTS
 2. CONFIG / CONSTANTS      NO_TOUCH_EXTS, VIDEO_EXTS, folder names, SKIP_PATH_PARTS
 3. TYPES / DATA CLASSES    DriveInfo, FileCandidate (NamedTuple)
 4. LOGGER SETUP            setup_logger()
 5. SAFETY GUARDS           is_no_touch(path), is_protected_path(path)
 6. DRIVE DETECTOR          detect_removable_drives() via ctypes.windll.kernel32
 7. UNDO LOG CLASS          record(), commit() (atomic .tmp+replace), load(), replay_reverse()
 8. EXECUTOR CLASS          move(), rename(), mkdir(), rmdir_if_empty(), _free_path()
                            dry_run flag lives HERE ONLY
 9. SCANNER / CLASSIFIERS   iter_files() via os.scandir (NOT glob/rglob)
                            parse_series_name(), parse_movie_name(), scan_drive()
10. OPERATIONS              op_rename_from_tsv(), op_organize_*(), op_cleanup_empty_dirs()
                            op_coherence_check(), op_generate_tsv(), op_undo()
11. MENU / UI               main_menu(), ask_dry_run(), pick_drive()
12. ENTRY POINT             main()
```

---

## 4. Top 5 Pitfalls

**P1 (CRITICAL) — Never use glob/rglob for file discovery.**
`[` and `]` are metacharacters — files like `Movie [1080p].mkv` are silently skipped. Use `os.scandir()` with a recursive stack. Already the reason Ordenar.ps1 uses `-LiteralPath` throughout.

**P2 (CRITICAL) — Guard against cross-drive moves.**
`shutil.move()` is atomic only when `src.drive == dst.drive`. Cross-drive = copy+delete = data loss on crash. Assert same drive in `Executor.move()`.

**P3 (CRITICAL) — Undo log breaks when drive letter changes on reconnect.**
Store drive-relative paths + volume serial number in log header. Resolve current drive letter at undo time via ctypes.

**P4 (CRITICAL) — ROM/ISO protection at every path-touching site, not just scan.**
The subtitle matcher and folder mover must also call `is_no_touch()`. A `.cue` file can be matched by a subtitle glob; a game folder can drag `.bin` files.

**P5 (HIGH) — Every `open()` must specify `encoding="utf-8"`.**
Windows defaults to `cp1252`. Spanish filenames silently corrupted otherwise. TSV reader uses `encoding="utf-8-sig"` for Excel BOM. `json.dump()` uses `ensure_ascii=False`.

---

## 5. Suggested Phase Structure

| Phase | Name | Delivers |
|-------|------|----------|
| 1 | Infrastructure | Config, safety guards, drive detection, Logger, UndoLog, Executor, Scanner |
| 2 | Core Operations | Apply TSV renames, organize series/movies/games, co-locate subs, empty-folder cleanup |
| 3 | Safety and UX | Undo/rollback UI, dry-run report, run summary, session marker |
| 4 | Power Features | TSV generator, coherence checker (misplaced files, gaps, duplicates) |

Phases 1+2 = working replacement for both PowerShell scripts. Phase 3 hardens it. Phase 4 makes it better.

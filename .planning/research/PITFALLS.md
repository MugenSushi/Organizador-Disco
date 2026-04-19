# Domain Pitfalls: Python Media File Organizer CLI (Windows)

**Domain:** File organizer CLI — videos, ROMs, ISOs on Windows removable drives
**Researched:** 2026-04-19
**Confidence:** HIGH (all critical claims verified against official Python 3 documentation)

---

## Critical Pitfalls

Mistakes that cause data loss, silent corruption, or require a rewrite to fix.

---

### Pitfall 1: glob / Path.glob Silently Skips Files With `[brackets]` in Filename

**What goes wrong:**
`glob.glob("*.mkv")`, `Path.glob("*.mkv")`, and `pathlib.rglob("*")` treat `[` and `]` as
character-class metacharacters (like regex `[abc]`). A file named
`Movie [1080p].mkv` may match zero results or a wrong subset.
The Ordenar.ps1 predecessor explicitly notes this problem with PowerShell's `-Path` flag and
uses `-LiteralPath` throughout. Python's glob has the exact same trap.

**Why it happens:**
Python's `glob` module implements Unix shell glob semantics. `[abc]` means "one character that
is a, b, or c". `[1080p]` matches a single character from the set {1,0,8,p}. The full filename
`Movie [1080p].mkv` is never matched by a plain `*.mkv` pattern when the path component
contains the brackets.

**Verified:** `glob.glob()` documentation confirms `glob.escape()` exists for exactly this reason.
`Path.glob()` / `Path.rglob()` have the same limitation (they share the same underlying engine).

**Consequences:**
- Files with `[tags]`, `[720p]`, `[BluRay]`, `[YIFY]` in their names are silently ignored.
- Series like `Doctor Who [2005] - Temporada 1 - Episodio 1.mkv` are never classified.
- No error is raised; the script appears to succeed while skipping entire categories of files.

**Prevention:**
- NEVER use `glob.glob()` or `Path.glob()` to discover files. Use `os.scandir()` / `os.walk()`
  (or `Path.iterdir()` recursively), then filter by extension in Python code.
- If glob patterns are absolutely needed (e.g., for TSV matching), wrap literal paths in
  `glob.escape(path)` before passing to any glob function.
- Apply filename matching via `Path.suffix.lower()` comparison against an allow-list, not via
  glob patterns.

**Warning signs in code:**
- `glob.glob(str(root) + "/**/*.mkv", recursive=True)`
- `Path(root).rglob("*.mp4")`
- Any `fnmatch.fnmatch()` call on a full path string containing brackets.

**Detection:**
Create a test file named `test [brackets].mkv` and confirm the scan finds it.

**Implementation phase:** Phase 1 (file scanning infrastructure). Must be right from the start;
fixing it later requires rewriting all scanning paths.

---

### Pitfall 2: `shutil.move` Across Drive Letters Is Copy-Then-Delete, Not Atomic

**What goes wrong:**
When `src` and `dst` are on different drive letters (e.g., `C:\temp\file.mkv` → `F:\Series\...`),
`shutil.move()` falls back to copy-then-delete: it copies the full file to the destination, then
removes the source. If the process is interrupted (power loss, Ctrl+C, exception) between those two
steps, the user ends up with the file at both locations or at neither.

This project operates on a single removable drive, so most moves are same-drive (safe, atomic
`os.rename()`). But if the log directory or temp work location is ever on a different drive, or if
the user accidentally triggers a cross-drive operation, the behavior silently changes.

**Verified:** `shutil.move()` documentation states: "If the destination is on the current
filesystem, then `os.rename()` is used. Otherwise, src is copied to the destination using
`copy_function` and then removed."

**Consequences:**
- Interrupted cross-drive move: source file is deleted but destination is a truncated partial copy.
- No rollback mechanism exists inside `shutil.move()` itself.
- The undo log will record the move as "pending" but the source file no longer exists.

**Prevention:**
- Assert that `src.drive == dst.drive` before any move operation. Raise a clear error if they
  differ (the project spec says all work stays on the selected removable drive).
- Add a `_same_drive_check(src: Path, dst: Path)` guard in the move helper. Never bypass it.
- For same-drive moves, `shutil.move()` uses `os.rename()` which is atomic on NTFS.

**Warning signs in code:**
- `shutil.move(src, dst)` without a prior drive-letter assertion.
- Log directory placed on the system drive (`C:\`) instead of the target drive.

**Detection:**
Inspect that `Path(src).drive == Path(dst).drive` before every move.

**Implementation phase:** Phase 1 (move helper / core operations). The drive assertion belongs
in the single move wrapper that all higher-level operations call.

---

### Pitfall 3: Undo Log Becomes Stale or Unresolvable

**What goes wrong:**
The undo log records `{"from": "F:\\Series\\Show\\S01E01.mkv", "to": "F:\\Video\\S01E01.mkv"}`.
Any of the following silently invalidates it:

1. **Drive letter changes on reconnect.** Windows may assign `G:\` instead of `F:\` next time.
   Absolute paths `F:\...` in the log now point nowhere. Undo silently does nothing or crashes.
2. **File moved again after logging.** User runs the organizer twice. The log from run 1 still
   shows the old `from` path, which no longer exists. Undo of run 1 is now impossible.
3. **Partial log write.** If the script crashes while appending entries to the undo log, the JSON
   file may be syntactically broken (truncated mid-record), making the entire undo session
   unloadable.
4. **Log file encoding mismatch.** Log written with default Windows encoding (`cp1252`) may fail
   to encode Spanish/Unicode filenames, silently replacing characters with `?`, making path
   reconstruction impossible.

**Prevention:**

1. **Drive-relative paths in the log.** Store `{"from": "Series\\Show\\S01E01.mkv", "to":
   "Video\\S01E01.mkv", "drive": "F:"}`. At undo time, discover the current drive letter of the
   mounted volume (by volume label or serial, via `ctypes`/`win32api`), then reconstruct full
   paths. Include volume serial number in the log header for validation.

2. **Write the undo log atomically.** Collect all undo entries in memory during a run, then write
   the complete JSON in a single `os.replace()` call after all operations succeed. Never append
   line-by-line to a JSON file. Use write-to-temp-then-rename:
   ```python
   tmp = log_path.with_suffix(".tmp")
   tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
   os.replace(tmp, log_path)
   ```

3. **Validate log before undo.** At undo startup, check that all `to` paths (current locations)
   exist before moving anything. Report discrepancies rather than silently skipping.

4. **Always open log files with `encoding="utf-8"`.** Never rely on the Windows default
   (`cp1252` / locale encoding). Spanish accents in `Películas`, `Temporada`, series names with
   tildes will be corrupted silently under `cp1252`.

**Warning signs in code:**
- `open(log_path, "w")` without `encoding="utf-8"`.
- `json.dump(..., ensure_ascii=True)` — paths become `\u00e9\u00f3\u00fa`, technically
  lossless but log is unreadable for manual inspection.
- Appending to log inside the per-file loop rather than writing once at the end.
- Storing absolute paths like `F:\...` without also storing the volume serial number.

**Detection:**
Disconnect and reconnect the drive to get a different letter, then attempt undo.

**Implementation phase:** Phase 1 (undo log data structure design). This cannot be retrofitted
easily. The schema for what is stored in the log must be decided before any operations are built.

---

### Pitfall 4: ROM/ISO Files Touched by Overly Broad Extension Matching

**What goes wrong:**
The extension allow-list for "no-touch" files is defined once and must be checked before every
single operation: scan, rename, move, subtitle matching, and empty-folder cleanup.
If any code path skips the check — even the subtitle mover — a ROM file with a matching-sounding
name pattern could be moved.

Concrete failure modes seen in similar tools:
- A `.bin` file (Sega CD ROM image) is inside a folder named like a video title. The movie mover
  sees the folder and moves it, dragging the `.bin` along.
- A subtitle-scanning loop looks at all files matching `<basename>.*` — if a `.cue` file shares
  the name of a video, it is silently moved as a "subtitle".
- Folder-cleanup step deletes a directory that appears empty to Python but contains hidden
  files or system files (e.g., `desktop.ini`), which may be alongside ROMs.

**Prevention:**
- Define `NO_TOUCH_EXTS` as a single frozenset at module level (mirror Ordenar.ps1's list exactly).
- Write a single `is_no_touch(path: Path) -> bool` predicate. Call it in every path-touching code
  path: scan filter, rename applicator, move operations, subtitle matcher, empty-folder cleanup.
- When moving a directory (Games reorganizer), enumerate its contents first. If ANY file inside
  has a no-touch extension, abort the whole directory move and log a warning.
- The subtitle matcher must check `is_no_touch()` on candidate sidecar files even though `.srt`
  and `.cue` do not overlap — future extension of the no-touch list could create overlap.

**Warning signs in code:**
- Extension check only in the scan phase, not in the move/rename phase.
- `if path.suffix in VIDEO_EXTS` without `and not is_no_touch(path)`.
- Subtitle loop using `path.parent.glob(stem + ".*")` — globs all extensions including `.bin`/`.cue`.

**Detection:**
Place a `.bin` file alongside a `.mkv` with the same stem. Verify the script never touches the
`.bin` in any operation mode.

**Implementation phase:** Phase 1 (core guards). Add to a `guards.py` or equivalent module.
All subsequent feature phases import and call this; the check must never be inline.

---

### Pitfall 5: Partial Execution Leaves Drive in Inconsistent State

**What goes wrong:**
The script processes N files. If it crashes at file K (KeyboardInterrupt, OSError, power loss),
files 1..K-1 have been moved and the undo log covers them. Files K..N have not been moved.
But files K+1..N may now have incorrect subtitles, since their video was moved but the subtitle
scan only happens after the video move in a coupled loop.

More critically: if the organizer creates destination directories before moving files into them,
a crash leaves empty directories scattered across the drive — confusing future runs.

**Prevention:**
- Write all undo entries in a single commit at the end (see Pitfall 3), but also write a
  checkpoint list progressively with a generation counter so a partial run is detectable.
- Use a "journal" pattern for the session: write a `.in_progress` marker file at the start,
  delete it at the end. If the script starts and finds `.in_progress`, warn the user that a
  previous run may have been interrupted, show what is in the undo log, offer to undo first.
- Create destination directories only immediately before moving a file into them, not in bulk at
  the start of each phase. This limits orphaned directories to at most one per interrupted move.
- Wrap the per-file move in a try/except that appends to an in-memory undo list. After each
  successful move, also persist a recovery checkpoint every N files (e.g., every 50).

**Warning signs in code:**
- `for system in ["PS1","PS2",...]: ensure_dir(dest)` at the top of a function before any moves.
- Single JSON write only at the very end of the entire run.
- No `.in_progress` or session marker.

**Detection:**
Send SIGINT (Ctrl+C) mid-run and inspect drive state.

**Implementation phase:** Phase 2 (operations implementation). The journal pattern is
infrastructure that all operation phases depend on.

---

## Moderate Pitfalls

Mistakes that degrade reliability but do not cause data loss if caught early.

---

### Pitfall 6: Windows MAX_PATH (260 chars) Silently Truncates or Errors

**What goes wrong:**
Windows historically limits paths to 260 characters (`MAX_PATH`). Deep directory structures
like `F:\Series\Breaking Bad\Temporada 5\Breaking Bad - Temporada 5 - Episodio 14 [1080p BluRay].mkv`
can exceed this limit. `pathlib` and `os` functions raise `OSError` or silently fail when they
encounter paths over 260 chars unless the system has long paths enabled.

**Verified:** Python docs state that long path support requires enabling "Enable Win32 long paths"
group policy OR setting `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`,
plus Python 3.6+.

**Prevention:**
- At script startup, check effective path length support:
  ```python
  import os
  test_path = "F:\\" + "a" * 250 + ".txt"
  # or check registry key
  ```
  More practically: at the start of each move, assert `len(str(dst)) < 250` and log a warning
  if the destination path approaches the limit. Do not silently truncate.
- Document in user-facing output that the script requires long paths enabled, OR add a startup
  check that reads the registry key via `winreg` and warns if it is not enabled.
- Keep folder names short in the generated structure: `Temporada 1` not `Temporada 01 - Completa`.

**Warning signs in code:**
- No path length check before constructing nested destination paths.
- Series names containing long titles combined with deep folder hierarchies.

**Detection:**
Use a series with a very long show name (>60 chars) and verify move succeeds.

**Implementation phase:** Phase 1 (move helper). Add a path length guard to the move wrapper.

---

### Pitfall 7: `open()` Without `encoding="utf-8"` Corrupts Spanish Filenames in Logs

**What goes wrong:**
On Windows, `open(path, "w")` uses the system locale encoding, typically `cp1252` for Spanish
Windows. This encoding cannot represent all Unicode characters (it covers only Latin-1 + Windows
extensions). Filenames containing characters outside cp1252 (e.g., Japanese titles in a mixed
collection, certain symbols) raise `UnicodeEncodeError` or are silently replaced.

Spanish-specific risk: `Películas`, `Corazón`, `Ñoño`, accented characters in series names.
`cp1252` handles most of these, but edge cases in the drive's content (e.g., anime titles) fail.

**Verified:** Python docs confirm `open()` uses `locale.getencoding()` when no encoding is given.
JSON docs confirm `json.dump(ensure_ascii=False)` requires explicit UTF-8 file encoding.

**Prevention:**
- Every `open()` call in the project must include `encoding="utf-8"`.
- All `json.dump()` calls must use `ensure_ascii=False` (human-readable) + UTF-8 file.
- The rename_plan.tsv reader must specify `encoding="utf-8"`. If the TSV was created by Excel or
  another Windows tool, it may be UTF-8-with-BOM; use `encoding="utf-8-sig"` to handle both.

**Warning signs in code:**
- `open(log_file, "w")` without encoding parameter.
- `csv.reader(f)` or `f.read()` on a TSV file opened without encoding.

**Detection:**
Create a file with a name containing `ñ`, `é`, `ü`. Verify log contains the correct characters.

**Implementation phase:** Phase 1 (I/O infrastructure). Applies to every file-write path:
log files, undo JSON, TSV reader.

---

### Pitfall 8: Race Condition — File In Use During Move

**What goes wrong:**
A video file currently being played in VLC or copied from another source is locked by Windows.
`shutil.move()` raises `PermissionError` (or `WinError 32: The process cannot access the file
because it is being used by another process`). If the script treats this as a fatal error and
aborts, partial moves from earlier in the same run may be left un-logged.

**Prevention:**
- Catch `PermissionError` and `OSError` per-file. Log the skip with `[LOCKED]` marker.
  Do NOT abort the entire run for a single locked file.
- For the undo log, a locked file that was not moved should never appear as a log entry.
- Optionally, detect files recently modified (within last 30 seconds) and skip them
  proactively: `time.time() - path.stat().st_mtime < 30`.
- If the script is run against the currently active media drive, accept that some files
  will be skipped and document this clearly.

**Warning signs in code:**
- `shutil.move(src, dst)` without per-file try/except that handles `PermissionError`.
- An exception in the move loop that propagates to break the loop entirely.

**Detection:**
Open a test file in VLC (keep it playing), run the organizer, verify: (a) it skips that file,
(b) the run completes for other files, (c) the locked file does not appear in the undo log.

**Implementation phase:** Phase 2 (all move operations). Error handling must be per-file.

---

### Pitfall 9: Recursive Scan Performance on Large Drives (10k+ Files)

**What goes wrong:**
`pathlib.Path.rglob("*")` on a 10k-file drive is slower than `os.scandir()` because `rglob`
materializes a generator but still makes one `stat()` call per entry. The bigger risk is memory:
collecting all results into a list `list(root.rglob("*"))` before processing can hold tens of
thousands of `Path` objects in RAM simultaneously.

Additional Windows-specific cost: antivirus software (Windows Defender) intercepts every
`os.stat()` call during a recursive scan, which can multiply scan time by 3-5x on large drives.

**Prevention:**
- Use `os.scandir()` with a manual recursive stack (or `os.walk()`) instead of `rglob`.
  `os.scandir()` returns `DirEntry` objects with cached `stat` information from the OS
  directory listing, avoiding redundant `stat()` syscalls.
  ```python
  def iter_files(root: Path):
      stack = [root]
      while stack:
          current = stack.pop()
          try:
              with os.scandir(current) as entries:
                  for entry in entries:
                      if entry.is_dir(follow_symlinks=False):
                          if not _is_excluded_dir(entry.path):
                              stack.append(Path(entry.path))
                      else:
                          yield Path(entry.path)
          except PermissionError:
              continue
  ```
- Skip known excluded directories (`_organizer_logs`, `$RECYCLE.BIN`, `System Volume Information`,
  `Juegos`, `_ORIG`) early — before descending into them — to prune the tree.
- Process files lazily (as a generator pipeline), never accumulate into a full list unless a
  second pass is truly required (e.g., duplicate detection).
- For a 10k-file scan, the expected time with `os.scandir()` + early pruning is under 5 seconds.
  If it exceeds 30 seconds, antivirus real-time protection is the likely culprit; document this.

**Verified:** Python docs confirm `os.scandir()` "gives better performance for many common use
cases" by combining directory listing with file attribute information in one OS call.

**Warning signs in code:**
- `list(Path(root).rglob("*"))` — full materialization before processing.
- `os.walk()` inside the already-excluded branches.
- No early-pruning of excluded directories.

**Detection:**
Time the scan on a drive with 5k+ files. If > 10 seconds, check for rglob usage or missing
directory exclusions.

**Implementation phase:** Phase 1 (scan infrastructure). The scan is the foundation; fixing
it later means refactoring all code that calls it.

---

## Minor Pitfalls

Mistakes that cause inconvenience or edge-case failures but are straightforward to fix.

---

### Pitfall 10: `Path.rename()` Raises `FileExistsError` on Windows (Unlike Unix)

**What goes wrong:**
On Unix, `Path.rename(dst)` silently overwrites `dst` if it exists. On Windows it raises
`FileExistsError`. Code copied from Unix examples or Stack Overflow answers will fail on
Windows when a destination filename already exists.

**Verified:** pathlib docs: "On Windows, if target exists, `FileExistsError` will be raised."

**Prevention:**
- Use `Path.replace(dst)` only when you intend to overwrite. For the deduplication case
  (file already exists at destination), use `get_free_path()` (like Ordenar.ps1's `Get-FreePath`)
  to find `filename (2).mkv`, `filename (3).mkv`, etc.
- Never use `Path.rename()` directly. Wrap all renames in a `safe_rename(src, dst)` helper
  that checks for collisions first.

**Implementation phase:** Phase 1 (move helper).

---

### Pitfall 11: Windows Reserved Filenames in Edge Cases

**What goes wrong:**
Filenames like `CON.mkv`, `NUL.mkv`, `PRN.srt`, `COM1.avi`, `LPT1.sub` are reserved device
names in Windows and cannot be created or opened normally. `Path("F:\\CON.mkv").exists()` may
behave unexpectedly. These are extremely rare in a video collection but a defensive guard
prevents cryptic errors.

**Verified:** Python 3.13+ adds `os.path.isreserved()`. For earlier versions, maintain a manual
set of reserved names.

**Prevention:**
- Add a guard in the move helper: if `dst.stem.upper()` is in `{"CON","NUL","PRN","AUX","COM1"...
  "COM9","LPT1"..."LPT9"}`, append an underscore to the stem before proceeding.
- Log the incident so the user is aware.

**Implementation phase:** Phase 1 (move helper), low priority.

---

### Pitfall 12: TSV rename_plan.tsv Created on Windows May Have UTF-8-BOM

**What goes wrong:**
If the user creates or edits `rename_plan.tsv` in Notepad or Excel, it will likely be saved as
UTF-8 with BOM (`\xef\xbb\xbf` at start). Reading it with `encoding="utf-8"` leaves the BOM in
the first field of the first row, causing the column header `old_path` to become `\ufeffold_path`
and breaking column lookup.

**Prevention:**
- Read the TSV with `encoding="utf-8-sig"`. This encoding transparently strips the BOM if
  present and falls back to normal UTF-8 if it is not.
- If using `csv.DictReader`, open the file with `utf-8-sig` before passing to the reader.

**Implementation phase:** Phase 2 (rename applicator). Single-line fix but easy to miss.

---

### Pitfall 13: Empty-Folder Cleanup Deletes Folders With Hidden Files

**What goes wrong:**
After moving all visible files out of a directory, `os.rmdir()` raises `OSError` if the directory
is not actually empty (Windows may leave `desktop.ini`, `Thumbs.db`, or junction points behind).
Worse, using `shutil.rmtree()` would delete those hidden files too — potentially from a ROM
directory if the guard is not in place.

**Prevention:**
- Use `os.rmdir()` (not `shutil.rmtree()`) for empty-folder cleanup. It raises an error if not
  truly empty, which is safe — log and skip, do not force-delete.
- Before calling `os.rmdir()`, confirm the folder is outside the no-touch scope.
- Do not attempt to delete folders that contain any no-touch extension files, even if those files
  are otherwise invisible (hidden attribute).

**Implementation phase:** Phase 3 (cleanup). Low risk if using `os.rmdir()` not `shutil.rmtree()`.

---

## Phase-Specific Warnings Summary

| Implementation Phase | Topic | Likely Pitfall | Mitigation |
|----------------------|-------|---------------|------------|
| Phase 1 — Core infrastructure | File scanning | Brackets in filenames silently skipped | Use `os.scandir()` + suffix filter, never glob |
| Phase 1 — Core infrastructure | Move helper | Cross-drive move becomes non-atomic | Assert same drive before every move |
| Phase 1 — Core infrastructure | I/O layer | Spanish filenames corrupted in logs | `encoding="utf-8"` on every `open()` call |
| Phase 1 — Core infrastructure | Undo log schema | Absolute paths break on drive letter change | Store relative paths + volume serial number |
| Phase 1 — Core infrastructure | Path lengths | Silent failure on long paths | Length guard in move helper |
| Phase 1 — Core infrastructure | Rename on Windows | `FileExistsError` differs from Unix | `safe_rename()` wrapper using `Path.replace()` |
| Phase 2 — Operations | Rename applicator | BOM in user-edited TSV | `encoding="utf-8-sig"` on TSV reader |
| Phase 2 — Operations | All move loops | Locked files abort entire run | Per-file `try/except PermissionError` |
| Phase 2 — Operations | ROM/ISO protection | Extension check missing in subtitle loop | `is_no_touch()` called at every path-touching site |
| Phase 2 — Operations | Partial execution | Crash leaves drive inconsistent | `.in_progress` session marker + atomic log write |
| Phase 3 — Cleanup | Empty folder removal | Hidden files cause `os.rmdir()` to silently fail or force-delete | Use `os.rmdir()` only, log failures, never `shutil.rmtree()` |
| Phase 4 — Undo | Undo reliability | Log stale after drive reconnect | Validate all `to` paths exist before executing any undo move |

---

## Sources

- Python 3 `shutil.move()` documentation — copy-then-delete behavior confirmed (HIGH confidence)
  https://docs.python.org/3/library/shutil.html#shutil.move
- Python 3 `glob` documentation — `glob.escape()` for literal bracket matching (HIGH confidence)
  https://docs.python.org/3/library/glob.html
- Python 3 Windows long path documentation — registry key + Python 3.6+ requirement (HIGH confidence)
  https://docs.python.org/3/using/windows.html
- Python 3 `pathlib.Path.rename()` documentation — `FileExistsError` on Windows confirmed (HIGH confidence)
  https://docs.python.org/3/library/pathlib.html
- Python 3 `open()` encoding documentation — Windows default is locale encoding, not UTF-8 (HIGH confidence)
  https://docs.python.org/3/library/functions.html#open
- Python 3 `json` documentation — `ensure_ascii` parameter, UTF-8 recommendation (HIGH confidence)
  https://docs.python.org/3/library/json.html
- Python 3 `os.scandir()` documentation — performance advantage over `os.listdir()` (HIGH confidence)
  https://docs.python.org/3/library/os.html#os.scandir
- Python 3 `os.path.isreserved()` documentation — Windows reserved names (HIGH confidence, Python 3.13+)
  https://docs.python.org/3/library/os.path.html
- Ordenar.ps1 (project file) — LiteralPath pattern used throughout as prior art for bracket problem

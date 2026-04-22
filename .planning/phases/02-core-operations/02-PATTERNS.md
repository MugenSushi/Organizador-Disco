# Phase 2: Core Operations - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 1 (single-file architecture: `organizer.py` additions)
**Analogs found:** 7 / 7 (organizer.py Phase 1 code + Ordenar.ps1 ground truth)

---

## File Classification

All Phase 2 work lands in a single file. Each logical unit is classified separately.

| New/Modified Unit | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `organizer.py` — SECTION 2 additions (VIDEO_EXTS, SUB_EXTS, CONSOLE_SYSTEMS, SCAN_EXCLUDE_DIR_NAMES) | config | — | `organizer.py` lines 14-36 (NO_TOUCH_EXTS, SKIP_PATH_PARTS) | exact |
| `organizer.py` — SECTION 9 (RE_SERIES, RE_MOVIE compiled patterns) | utility | transform | `organizer.py` SECTION 2 frozenset constants | role-match |
| `organizer.py` — `apply_renames()` | service | CRUD (file-I/O) | `Ordenar.ps1` lines 122-161 + `Renombrar.ps1` lines 41-59 | exact (direct translation) |
| `organizer.py` — `_scan_videos_recursive()` + `_walk()` | utility | file-I/O | `organizer.py` SECTION 7 `Executor.move()` os.scandir pattern | role-match |
| `organizer.py` — `_organize_games()` | service | CRUD (file-I/O) | `Ordenar.ps1` lines 174-191 | exact (direct translation) |
| `organizer.py` — `_move_subtitles()` | utility | file-I/O | `Ordenar.ps1` lines 256-268, 296-309 | exact (direct translation) |
| `organizer.py` — `_remove_empty_dirs()` | utility | file-I/O | `Ordenar.ps1` implicit (no PS1 equivalent — design from ORG-05) | partial |
| `organizer.py` — `organize_videos_and_games()` | service | CRUD (file-I/O) | `Ordenar.ps1` lines 199-310 | role-match (orchestrator wrapper is new) |
| `organizer.py` — `show_menu()` update + `_print_summary()` | controller | event-driven | `organizer.py` lines 215-238 (current `show_menu()`) | exact |

---

## Pattern Assignments

### Constants additions to SECTION 2

**Analog:** `organizer.py` lines 14-36 (existing frozenset and tuple constants)

**Pattern to copy** (`organizer.py` lines 17-36):
```python
# Use frozenset for O(1) membership test on extensions
NO_TOUCH_EXTS: frozenset[str] = frozenset({
    ".iso", ".bin", ...
})
# Use tuple for ordered sequences (SKIP_PATH_PARTS)
SKIP_PATH_PARTS: tuple[str, ...] = (...)
# Plain string constant for single values
LOG_DIR_NAME = "_organizer_logs"
```

**New constants to add after existing SECTION 2:**
```python
# SECTION 2 additions — Phase 2 constants

VIDEO_EXTS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".mpg", ".mpeg", ".ts",
})

SUB_EXTS: tuple[str, ...] = (".srt", ".ass", ".sub", ".idx")

# Ground truth: Ordenar.ps1 lines 172-192. PC and Steam intentionally absent (D-04 locked).
CONSOLE_SYSTEMS: tuple[str, ...] = ("PS1", "PS2", "PSP", "GBA", "GBC")

# Claude's discretion — confirmed in 02-UI-SPEC.md. Lowercase for case-insensitive comparison.
SCAN_EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "_organizer_logs", "series", "peliculas", "juegos",
})
```

**Rule:** All extension sets use `frozenset` (O(1) lookup). Ordered sequences use `tuple`. All strings lowercase (matched via `.lower()`).

---

### SECTION 9 — Compiled regex patterns

**Analog:** `organizer.py` lines 14-36 pattern (module-level constants); `Ordenar.ps1` lines 236 and 278 (ground-truth regex)

**Ground truth PS1 source** (`Ordenar.ps1` lines 236, 278):
```powershell
# Series (line 236):
if ($baseName -match "^(?<show>.+?)\s-\sTemporada\s(?<season>\d+)\s-\sEpisodio\s(?<ep>\d+).*")

# Movies (line 278):
if ($baseName -match "^(?<t>.+?)\s\((?<y>19\d{2}|20\d{2})\).*")
```

**Python translation — compile at module level, never inside a loop** (CLAUDE.md: `re.compile at module level`):
```python
# SECTION 9 — Compiled regex patterns (Phase 2)
# Ground truth: Ordenar.ps1 line 236 (series) and line 278 (movies)
# Compiled at module level — never inside a function or loop

RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)

RE_MOVIE = re.compile(
    r"^(?P<title>.+?)\s\((?P<year>(?:19|20)\d{2})\)",
    re.IGNORECASE,
)
```

**Named groups over numbered groups** — CLAUDE.md convention and PS1 ground truth both use named groups.

---

### `apply_renames(executor, drive_root)` — SECTION 10

**Analog:** `Ordenar.ps1` lines 122-161; `Renombrar.ps1` lines 41-59

**Ground truth PS1 source** (`Ordenar.ps1` lines 122-161):
```powershell
Import-Csv -LiteralPath $PLAN_FILE -Delimiter "`t" | ForEach-Object {
  $old = $_.old_path
  $new = $_.new_path
  if ([string]::IsNullOrWhiteSpace($old) -or [string]::IsNullOrWhiteSpace($new)) { return }
  if (-not (Test-Path -LiteralPath $old)) {
    "[SKIP] No existe: $old" | Out-File $LOG_APPLY -Append
    return
  }
  $final = Get-FreePath $new
  try {
    Rename-Item -LiteralPath $old -NewName (Split-Path $final -Leaf) -ErrorAction Stop
    "[OK] RENAME: $old -> $final" | Out-File $LOG_APPLY -Append
  }
  catch [System.UnauthorizedAccessException] { "[DENY] ..." }
  catch { "[ERR] ..." }
}
```

**TSV opening pattern** (`organizer.py` SECTION 1 + CLAUDE.md csv guidance):
```python
# csv.DictReader with these exact parameters — handles BOM from Excel (utf-8-sig),
# quoted fields, and tab delimiter. newline='' is required by csv module spec.
with open(plan_file, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter="\t")
    rows = list(reader)
```

**Row validation pattern** (translates PS1 `IsNullOrWhiteSpace` + `Test-Path -LiteralPath`):
```python
for i, row in enumerate(rows, 1):
    old_str = (row.get("old_path") or "").strip()
    new_str = (row.get("new_path") or "").strip()
    if not old_str or not new_str:
        logger.warning("Fila %d ignorada: faltan columnas old_path / new_path.", i)
        continue
    counts["procesados"] += 1
    src = Path(old_str)   # literal — Path() never glob-expands (equivalent to -LiteralPath)
    if not src.exists():
        logger.warning("SKIP (no existe): %s", src)
        counts["saltados"] += 1
        continue
    dst = Path(new_str)
    result = executor.move(src, dst)
    if result is not None:
        counts["movidos"] += 1
    else:
        counts["errores"] += 1
```

**Missing file feedback** (CLAUDE.md: `print()` only for user-visible messages, not operational log):
```python
if not plan_file.exists():
    print(f"No se encontro rename_plan.tsv en {drive_root}. "
          "Coloca el archivo y vuelve a intentarlo.")
    return counts
```

**Counter dict pattern** — same shape returned by all Phase 2 operation functions:
```python
counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
```

---

### `_scan_videos_recursive(root, exclude_roots)` + `_walk()` — SECTION 11

**Analog:** `organizer.py` SECTION 7 `Executor.move()` (os.scandir pattern); `Ordenar.ps1` lines 207-229 (`Is-ExcludedDir` and `Get-ChildItem -Recurse`)

**Ground truth PS1 source** (`Ordenar.ps1` lines 207-229):
```powershell
$excludeDirs = @(
  (Join-Path $DISK_ROOT "_organizer_logs"),
  (Join-Path $DISK_ROOT "_ORIG"),
  (Join-Path $DISK_ROOT "Juegos")
)
function Is-ExcludedDir($fullPath) {
  foreach ($d in $excludeDirs) {
    if ($fullPath -like "$d*") { return $true }
  }
  return $false
}
# ... then:
if (Is-ExcludedDir $full) { return }
```

**os.scandir traversal pattern** (INFRA-05 — never glob/rglob; copy from Phase 1 PATTERNS.md Shared Patterns):
```python
# ALWAYS os.scandir with context manager — never glob, never rglob (INFRA-05)
# follow_symlinks=False on both is_dir and is_file checks
with os.scandir(current) as it:
    for entry in it:
        if entry.is_dir(follow_symlinks=False):
            # process subdirectory
        elif entry.is_file(follow_symlinks=False):
            # process file
```

**Exclusion-at-root-only pattern** (translates PS1's `$fullPath -like "$d*"` for top-level dirs):
```python
# Apply exclusions only when current directory IS the drive root.
# Matches PS1 semantics: only subtrees rooted at excluded dirs are skipped.
if current == drive_root and entry.name.lower() in exclude_roots:
    continue
```

**PermissionError handling pattern** (copy from `organizer.py` lines 139-141):
```python
except PermissionError:
    logger.warning("SKIP (permiso denegado): %s", current)
```

---

### `_organize_games(executor, drive_root, counts)` — inside SECTION 13

**Analog:** `Ordenar.ps1` lines 174-191

**Ground truth PS1 source** (`Ordenar.ps1` lines 174-191):
```powershell
$systems = @("PC","PS1","PS2","PSP","GBA","GBC")
foreach ($sys in $systems) {
  $src = Join-Path $DISK_ROOT $sys
  if (Test-Path -LiteralPath $src) {
    $dest = Join-Path $JUEGOS_ROOT $sys
    Ensure-Dir $dest
    Get-ChildItem -LiteralPath $src -ErrorAction SilentlyContinue | ForEach-Object {
      $target = Join-Path $dest $_.Name
      $target2 = Get-FreePath $target
      try {
        Move-Item -LiteralPath $_.FullName -Destination $target2 -ErrorAction Stop
      } catch { "[ERR] MOVE GAME: ..." }
    }
  }
}
```

**Python translation pattern:**
```python
# D-04: CONSOLE_SYSTEMS tuple has PC and Steam removed — silent skip by omission, no warning
for sys_name in CONSOLE_SYSTEMS:
    src_dir = drive_root / sys_name
    if not src_dir.exists():
        continue                          # silent — no warning; dir simply absent
    dst_dir = drive_root / "Juegos" / sys_name
    try:
        with os.scandir(src_dir) as it:
            for entry in it:             # move CONTENTS, not the folder itself
                counts["procesados"] += 1
                result = executor.move(Path(entry.path), dst_dir / entry.name)
                if result is not None:
                    counts["movidos"] += 1
                else:
                    counts["errores"] += 1
    except PermissionError:
        logger.warning("SKIP (permiso denegado): %s", src_dir)
```

**Critical:** Iterate `os.scandir(src_dir)` and move each `entry`, not `src_dir` itself. Moving the folder gives `Juegos\PS1\PS1\` — ground truth moves contents (PS1 line 181: `Get-ChildItem -LiteralPath $src | ForEach-Object`).

---

### `_move_subtitles(executor, video_src, video_dst_dir, counts)` — inside SECTION 13

**Analog:** `Ordenar.ps1` lines 256-268 (series subs) and 296-309 (movie subs)

**Ground truth PS1 source** (`Ordenar.ps1` lines 257-268):
```powershell
foreach ($se in $SUB_EXTS) {
  $subPath = Join-Path $file.DirectoryName ($file.BaseName + $se)
  if (Test-Path -LiteralPath $subPath) {
    $destSub = Join-Path $seasonDir ([System.IO.Path]::GetFileName($subPath))
    $destSub = Get-FreePath $destSub
    try {
      Move-Item -LiteralPath $subPath -Destination $destSub -ErrorAction Stop
    } catch { "[ERR] MOVE SUB: ..." }
  }
}
```

**Python translation pattern:**
```python
# Called only after a successful video move (result is not None — Pitfall 3)
def _move_subtitles(executor, video_src: Path, video_dst_dir: Path, counts: dict) -> None:
    stem = video_src.stem
    src_dir = video_src.parent       # same directory as video (not recursive — ground truth A1)
    for ext in SUB_EXTS:
        sub_src = src_dir / (stem + ext)
        if sub_src.exists():
            counts["procesados"] += 1
            result = executor.move(sub_src, video_dst_dir / sub_src.name)
            if result is not None:
                counts["movidos"] += 1
            else:
                counts["errores"] += 1
```

**Calling convention — gate on video move result:**
```python
result = executor.move(video_path, dst_dir / video_path.name)
if result is not None:
    counts["movidos"] += 1
    _move_subtitles(executor, video_path, result.parent, counts)  # use result.parent, not dst_dir
else:
    counts["errores"] += 1
```

**Note:** Pass `result.parent` (the actual final destination, which may have a collision-safe suffix from `_free_path`) rather than the pre-computed `dst_dir`.

---

### `_remove_empty_dirs(root, counts_removed)` — SECTION 12

**Analog:** No PS1 equivalent. Design from ORG-05 requirement and RESEARCH.md Pattern 6.

**os.rmdir safety contract:**
```python
# Path.rmdir() (stdlib wrapper for os.rmdir) raises OSError if directory is not empty.
# This is the safe contract — it can never delete a non-empty directory.
# shutil.rmtree is explicitly forbidden (ORG-05, REQUIREMENTS.md).
try:
    child.rmdir()   # only succeeds if empty — OSError otherwise
    counts_removed.append(child)
    logger.debug("RMDIR: %s", child)
except OSError:
    pass            # not empty or permission denied — skip silently (acceptable per ORG-05)
```

**Bottom-up traversal pattern** (recurse into children before attempting rmdir on parent):
```python
# Bottom-up: recurse FIRST, then try rmdir on current node.
# Top-down fails: parent still has children when visited.
for entry in entries:
    if entry.is_dir(follow_symlinks=False):
        if entry.name.lower() in CLEANUP_EXCLUDE_NAMES:
            continue
        child = Path(entry.path)
        _remove_empty_dirs(child, counts_removed)   # recurse first
        try:
            child.rmdir()
            ...
        except OSError:
            pass
```

**Log level:** `logger.debug()` for successful rmdir — this is diagnostic detail, not user-facing. Per CLAUDE.md: `logger.debug("...")` for diagnostic detail.

---

### `organize_videos_and_games(executor, drive_root)` — SECTION 13

**Analog:** `Ordenar.ps1` lines 199-310 (full series/movies/subs block); orchestrator wrapper is new.

**Ground truth PS1 source** (`Ordenar.ps1` lines 199-204):
```powershell
$SERIES_ROOT    = Join-Path $DISK_ROOT "Series"
$PELICULAS_ROOT = Join-Path $DISK_ROOT "Peliculas"
Ensure-Dir $SERIES_ROOT
Ensure-Dir $PELICULAS_ROOT
```

**Series path construction** (`Ordenar.ps1` lines 237-241):
```powershell
$show   = $Matches["show"].Trim()
$season = [int]$Matches["season"]
$showDir   = Join-Path $SERIES_ROOT $show
$seasonDir = Join-Path $showDir ("Temporada " + $season)
```

**Python translation:**
```python
show = m_series.group("show").strip()
season = int(m_series.group("season"))
dst_dir = drive_root / "Series" / show / f"Temporada {season}"
```

**Movie path construction** (`Ordenar.ps1` lines 275-280):
```powershell
$movieFolderName = $baseName.Trim()                                    # fallback
if ($baseName -match "^(?<t>.+?)\s\((?<y>19\d{2}|20\d{2})\).*") {
    $movieFolderName = ($Matches["t"].Trim() + " (" + $Matches["y"] + ")")
}
```

**Python translation (ground truth assumption A2 — fallback uses full stem):**
```python
m_movie = RE_MOVIE.match(stem)
if m_movie:
    folder = f"{m_movie.group('title').strip()} ({m_movie.group('year')})"
else:
    folder = stem.strip()              # fallback: full stem, matches PS1 line 275
dst_dir = drive_root / "Peliculas" / folder
```

**Orchestrator structure:**
```python
def organize_videos_and_games(executor, drive_root: Path) -> dict:
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)

    # Step 1: Game console folders first (ORG-03)
    _organize_games(executor, drive_root, counts)

    # Step 2: Scan remaining videos (ORG-01, ORG-02)
    exclude_top = frozenset({"_organizer_logs", "series", "peliculas", "juegos"})
    video_files = _scan_videos_recursive(drive_root, exclude_top)

    if not video_files:
        print("No se encontraron archivos de video para organizar.")
        return counts

    for video_path in video_files:
        counts["procesados"] += 1
        stem = video_path.stem
        m_series = RE_SERIES.match(stem)
        if m_series:
            ...   # series path construction
        else:
            ...   # movie path construction
        result = executor.move(video_path, dst_dir / video_path.name)
        if result is not None:
            counts["movidos"] += 1
            _move_subtitles(executor, video_path, result.parent, counts)
        else:
            counts["errores"] += 1

    # Step 3: Cleanup (ORG-05)
    removed = []
    _remove_empty_dirs(drive_root, removed)

    return counts
```

---

### `show_menu()` update + `_print_summary()` — SECTION 14

**Analog:** `organizer.py` lines 215-238 (current `show_menu()` stub)

**Current implementation** (`organizer.py` lines 215-238):
```python
def show_menu(executor: Executor, drive: dict) -> None:
    while True:
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar videos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir ultima operacion")
        print("  4) Detectar incoherencias")
        print("  0) Salir")
        choice = input("Opcion: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("(Disponible en Fase 2)")
        elif choice == "2":
            print("(Disponible en Fase 2)")
        elif choice == "3":
            print("(Disponible en Fase 3)")
        elif choice == "4":
            print("(Disponible en Fase 4)")
        else:
            print("Opcion invalida.")
```

**Phase 2 update pattern** — add option 5 to print block, replace stubs 1-2, wire dry-run toggle:
```python
def show_menu(executor: Executor, drive: dict) -> None:
    while True:
        dry_label = "ON" if executor.dry_run else "OFF"
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar videos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir ultima operacion")
        print("  4) Detectar incoherencias")
        print(f"  5) Dry-run: {dry_label}")          # D-01: toggle shows current state
        print("  0) Salir")
        choice = input("Opcion: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            counts = organize_videos_and_games(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "2":
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "3":
            print("(Disponible en Fase 3)")
        elif choice == "4":
            print("(Disponible en Fase 4)")
        elif choice == "5":
            executor.dry_run = not executor.dry_run   # D-01: attribute flip, no reconstruction
                                                       # D-02: no extra feedback — label updates on next reprint
        else:
            print("Opcion invalida.")
```

**Summary printer** (MENU-03 — `print()` not `logger`, one line, `\u2713` escape for Windows cp1252 safety):
```python
def _print_summary(counts: dict) -> None:
    """MENU-03: one-line summary. Uses print() not logger (user-visible). \u2713 escapes cp1252."""
    p = counts.get("procesados", 0)
    m = counts.get("movidos", 0)
    s = counts.get("saltados", 0)
    e = counts.get("errores", 0)
    print(f"\u2713 Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")
```

---

## Shared Patterns

### Error Handling in File Operations

**Source:** `organizer.py` lines 136-144 (`Executor.move()`) — established in Phase 1
**Apply to:** `_organize_games()`, `_scan_videos_recursive()`, `_remove_empty_dirs()`

```python
# Two-level catch — specific first, broad OSError second
# Copy from Executor.move() (organizer.py lines 136-144)
try:
    shutil.move(str(src), str(final_dst))
    logger.info("MOVE: %s -> %s", src, final_dst)
except PermissionError:
    logger.error("DENY: %s (acceso denegado)", src)
    return None
except OSError as exc:
    logger.error("ERR: %s : %s", src, exc)
    return None

# For scandir blocks (not moves):
except PermissionError:
    logger.warning("SKIP (permiso denegado): %s", path)
```

### Logging Call Pattern

**Source:** `organizer.py` lines 39, 126-143 (module-level logger + usage in Executor)
**Apply to:** All four new functions

```python
logger = logging.getLogger("organizer")   # module-level — already defined

# In new functions:
logger.warning("SKIP (...): %s", path)    # blocks/skips — WARNING level
logger.info("MOVE: %s -> %s", src, dst)   # successful ops — INFO level (via Executor)
logger.error("ERR: %s : %s", path, exc)   # failures — ERROR level (via Executor)
logger.debug("RMDIR: %s", path)            # diagnostic detail — DEBUG level
```

Do NOT use `print()` for operational messages — only `_print_summary()` and missing-file user prompts use `print()`.

### Path Construction Pattern

**Source:** `organizer.py` lines 100-112 (`_free_path()`) and CLAUDE.md tech stack
**Apply to:** All path construction in Phase 2 functions

```python
# / operator always — never os.path.join or string concatenation
dst_dir = drive_root / "Series" / show / f"Temporada {season}"
dst = dst_dir / video_path.name

# Always str() when passing to shutil or os functions
shutil.move(str(src), str(final_dst))   # inside Executor — call sites use executor.move()
```

### Executor.move() as Single Mutation Point

**Source:** `organizer.py` lines 121-145
**Apply to:** Every file move in all four new functions (NEVER call `shutil.move()` directly at call sites)

```python
# Call sites always go through executor.move()
result = executor.move(src, dst)
if result is not None:
    counts["movidos"] += 1
else:
    counts["errores"] += 1
# Safety guards (is_no_touch, should_skip_path, _free_path, dry_run) are enforced INSIDE move()
```

### Counter Dict Pattern

**Source:** RESEARCH.md — all operation functions return same-shaped dict
**Apply to:** `apply_renames()`, `organize_videos_and_games()`, passed by reference into helpers

```python
counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
# Passed by reference into _organize_games(), _move_subtitles() so they can accumulate
# Returned to show_menu() which passes to _print_summary()
```

### os.scandir Directory Traversal

**Source:** Phase 1 PATTERNS.md Shared Patterns + `organizer.py` SECTION 7 established rule (INFRA-05)
**Apply to:** `_walk()`, `_organize_games()`, `_remove_empty_dirs()`

```python
# ALWAYS context manager form — handles cleanup on PermissionError
with os.scandir(directory) as it:
    for entry in it:
        if entry.is_dir(follow_symlinks=False):
            ...
        elif entry.is_file(follow_symlinks=False):
            ...
# Never glob.glob(), Path.glob(), or Path.rglob() — silently skips files with [ ] in name
```

---

## No Analog Found

| Unit | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `_remove_empty_dirs()` — bottom-up cleanup | utility | file-I/O | No PS1 equivalent. Ordenar.ps1 has no empty-dir cleanup step. Design from ORG-05 + RESEARCH.md Pattern 6. |

For `_remove_empty_dirs()`, follow RESEARCH.md Pattern 6 directly — it is a fully verified design with no ambiguity.

---

## Internal Module Section Order

Phase 2 additions slot into the established section numbering from RESEARCH.md:

```
SECTION 1  — stdlib imports (unchanged — all needed imports already present)
SECTION 2  — Constants (ADD: VIDEO_EXTS, SUB_EXTS, CONSOLE_SYSTEMS, SCAN_EXCLUDE_DIR_NAMES)
SECTION 3  — Module-level logger (unchanged)
SECTION 4  — Drive detection helpers (unchanged)
SECTION 5  — Safety helpers (unchanged)
SECTION 6  — _free_path helper (unchanged)
SECTION 7  — Executor class (unchanged)
SECTION 8  — Logging setup + select_drive (unchanged)
SECTION 9  — [NEW] RE_SERIES, RE_MOVIE compiled at module level
SECTION 10 — [NEW] apply_renames(executor, drive_root) -> dict
SECTION 11 — [NEW] _scan_videos_recursive(root, exclude_roots) -> list[Path]
             [NEW] _walk(drive_root, current, exclude_roots, acc) -> None
SECTION 12 — [NEW] _remove_empty_dirs(root, counts_removed) -> None
SECTION 13 — [NEW] _organize_games(executor, drive_root, counts) -> None
             [NEW] _move_subtitles(executor, video_src, video_dst_dir, counts) -> None
             [NEW] organize_videos_and_games(executor, drive_root) -> dict
SECTION 14 — Main menu + entry point (UPDATED show_menu: option 5, wire options 1-2)
             [NEW] _print_summary(counts) -> None
```

---

## Metadata

**Analog search scope:** `organizer.py` (Phase 1 implementation), `Ordenar.ps1`, `Renombrar.ps1`
**Files scanned:** `organizer.py` (255 lines), `Ordenar.ps1` (317 lines), `Renombrar.ps1` (67 lines), `01-PATTERNS.md`
**Pattern extraction date:** 2026-04-19
**Ground-truth precedence:** `Ordenar.ps1` > `REQUIREMENTS.md` for operational logic (per CONTEXT.md canonical refs)

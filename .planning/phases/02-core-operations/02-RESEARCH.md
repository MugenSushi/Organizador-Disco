# Phase 2: Core Operations - Research

**Researched:** 2026-04-19
**Domain:** Python stdlib file operations — TSV rename, recursive video/game organizer, subtitle co-location, empty-folder cleanup
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Dry-run se activa/desactiva con la **opcion 5 del menu principal**: `5) Dry-run: OFF` → al pulsarla cambia a `5) Dry-run: ON`. Toggle numerado visible en el menu en todo momento.
- **D-02:** Con dry-run activo, al elegir una operacion (1 o 2) esta **se ejecuta en seco directamente**, sin confirmacion ni aviso extra.
- **D-03:** El estado dry-run **persiste hasta que el usuario lo desactiva manualmente**. No se reinicia entre operaciones.
- **D-04:** La carpeta `PC\` (y `Steam\` si existe en la raiz de la unidad) se **excluyen completamente** de ORG-03. Solo se organizan las carpetas de consola: `PS1`, `PS2`, `PSP`, `GBA`, `GBC`.
- **D-05:** Las exclusiones de `SKIP_PATH_PARTS` ya definidas en Phase 1 son suficientes para el resto. No se anaden exclusiones adicionales.

### Claude's Discretion

- **Ambito del escaneo al organizar** — Excluir `_organizer_logs\`, `Juegos\`, `Series\`, `Peliculas\` de la busqueda de Series/Peliculas para evitar doble-organizacion. (Confirmed: 02-UI-SPEC.md)
- **Formato de rutas en rename_plan.tsv** — Rutas absolutas (e.g., `E:\Videos\old name.mkv`). (Confirmed: 02-UI-SPEC.md)
- **Formato del resumen final (MENU-03)** — `✓ Procesados: N | Movidos: N | Saltados: N | Errores: N` — una linea compacta antes de volver al menu. (Confirmed: 02-UI-SPEC.md)
- **Estructura interna de modulos** — Claude organiza las funciones de Phase 2 dentro de `organizer.py` segun los patrones establecidos en Phase 1.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RENAME-01 | Aplicar renombrados desde rename_plan.tsv existente (columnas old_path / new_path, separador tab) | csv.DictReader with delimiter='\t', encoding='utf-8-sig' — verified in CLAUDE.md and Phase 1 patterns |
| RENAME-02 | El aplicador usa rutas literales (sin interpretar comodines) | Path(row['old_path']) direct construction — no glob expansion; Ordenar.ps1 uses -LiteralPath as ground truth |
| ORG-01 | Videos con patron "Show - Temporada X - Episodio Y" → Series\<Show>\Temporada X\ | Regex from Ordenar.ps1 line 236 — exact pattern confirmed |
| ORG-02 | Videos con patron "Titulo (Año)" → Peliculas\<Titulo (Año)>\ | Regex from Ordenar.ps1 line 278 — exact pattern confirmed |
| ORG-03 | Carpetas PS1, PS2, PSP, GBA, GBC → Juegos\<sistema>\ (contenido, no la carpeta) | Ordenar.ps1 lines 174-191 — move contents via os.scandir, not the folder itself |
| ORG-04 | Subtitulos (.srt .ass .sub .idx) con mismo basename que video movido → junto al video | Ordenar.ps1 lines 256-268, 296-309 — check each SUB_EXT for same-basename file in source dir |
| ORG-05 | Carpetas vacias eliminadas tras organizar (os.rmdir, nunca shutil.rmtree) | os.rmdir only removes empty dirs — safe by contract; bottom-up traversal order required |
| MENU-02 | Desde el menu se puede activar modo dry-run antes de ejecutar cualquier operacion | executor.dry_run = not executor.dry_run on option 5; D-01 through D-03 locked |
| MENU-03 | Al finalizar cualquier operacion se muestra resumen: procesados, movidos, saltados, errores | print() one-liner format locked in D-Discretion and 02-UI-SPEC.md |
</phase_requirements>

---

## Summary

Phase 2 adds all file-moving operations to the existing `organizer.py` skeleton built in Phase 1. The foundation is already in place: `Executor.move()` handles all safety checks, dry-run gating, collision avoidance, and error logging. Phase 2 only needs to wire in the four operation functions and update `show_menu()`.

The PowerShell reference implementations (`Ordenar.ps1`, `Renombrar.ps1`) are the authoritative ground truth for regex patterns and operational logic. All patterns have been extracted and are ready for direct translation to Python. The traversal strategy uses `os.scandir` exclusively (INFRA-05, already established) to correctly handle bracket characters in filenames.

The primary risk area is the recursive scanner for ORG-01/ORG-02: it must exclude already-organized destination folders (`Series\`, `Peliculas\`, `Juegos\`, `_organizer_logs\`) to prevent double-moves in subsequent runs. The empty-folder cleanup (ORG-05) must traverse bottom-up to ensure parent folders are cleaned after child folders are removed.

**Primary recommendation:** Implement four new functions (`apply_renames`, `organize_videos_and_games`, `_scan_videos_recursive`, `_remove_empty_dirs`) plus update `show_menu()`. All functions call `Executor.move()` and return a summary counter dict.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TSV parsing | organizer.py — apply_renames() | csv.DictReader | All logic stays in single .py file per architecture decision |
| Recursive video scan | organizer.py — _scan_videos_recursive() | os.scandir | Discovery layer; feeds into organizer |
| Series/movie classification | organizer.py — organize_videos_and_games() | re compiled patterns | Pattern matching decides destination path |
| File movement (all operations) | organizer.py — Executor.move() | shutil.move | Single mutation point; safety enforced here |
| Game folder reorganization | organize_videos_and_games() | Executor.move | os.scandir over system folder contents |
| Subtitle co-location | organize_videos_and_games() | Executor.move | Triggered immediately after video move |
| Empty folder cleanup | _remove_empty_dirs() | os.rmdir | Post-organize pass; bottom-up traversal |
| Dry-run toggle | show_menu() | Executor.dry_run | Attribute flip; no reconstruction |
| Operation summary | show_menu() → print() | per-op counter dict | print() not logger; user-visible feedback |

---

## Standard Stack

### Core (all stdlib — zero pip installs)

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `csv` | 3.x stdlib | Read rename_plan.tsv | `DictReader(delimiter='\t', encoding='utf-8-sig')` handles BOM and quoted fields |
| `re` | 3.x stdlib | Match series/movie filenames | Compile at module level; named groups over numbered groups |
| `os` | 3.x stdlib | `os.scandir` for traversal, `os.rmdir` for empty dir removal | scandir avoids glob bracket issue; rmdir is atomic safe |
| `pathlib.Path` | 3.x stdlib | All path construction | Established in Phase 1; / operator, .stem, .suffix |
| `shutil` | 3.x stdlib | File moves via Executor | Already routed through Executor.move() |
| `logging` | 3.x stdlib | Per-file feedback | Named logger already configured — no change needed |

[VERIFIED: organizer.py — all modules already imported in Phase 1 skeleton]

### No new dependencies required

Phase 2 adds zero new imports to `organizer.py`. All required modules are already imported.

---

## Architecture Patterns

### System Architecture Diagram

```
User input (menu option 1 or 2)
          |
          v
    show_menu()
          |
    +-----------+----------+
    |                      |
option 1                option 2
    |                      |
organize_videos_and_games()   apply_renames()
    |                      |
    +-----------+          csv.DictReader
    |           |             |
_scan_videos   scan game     for each row:
_recursive()   system dirs    Path(old) → Executor.move(src, dst)
    |           |
    v           v
classify:    Executor.move(content, Juegos\sys\)
series / movie
    |
Executor.move(video, Series\...\  or  Peliculas\...\)
    |
for each SUB_EXT: check same-basename sub in src dir
    |
Executor.move(sub, beside video)
    |
_remove_empty_dirs(drive root)
    |
os.rmdir (bottom-up, only if empty)
    |
print summary one-liner
    |
show_menu() reprints
```

### Recommended Project Structure

```
organizer.py
├── SECTION 1  — stdlib imports (unchanged)
├── SECTION 2  — Constants (add VIDEO_EXTS, SUB_EXTS, CONSOLE_SYSTEMS, SCAN_EXCLUDE_DIRS_NAMES)
├── SECTION 3  — Module-level logger (unchanged)
├── SECTION 4  — Drive detection helpers (unchanged)
├── SECTION 5  — Safety helpers (unchanged)
├── SECTION 6  — _free_path helper (unchanged)
├── SECTION 7  — Executor class (unchanged)
├── SECTION 8  — Logging setup + select_drive (unchanged)
├── SECTION 9  — [NEW] Regex patterns (compiled at module level)
├── SECTION 10 — [NEW] apply_renames(executor, drive_root) -> dict
├── SECTION 11 — [NEW] _scan_videos_recursive(root, exclude_roots) -> list[Path]
├── SECTION 12 — [NEW] _remove_empty_dirs(root, exclude_roots) -> int
├── SECTION 13 — [NEW] organize_videos_and_games(executor, drive_root) -> dict
└── SECTION 14 — Main menu + entry point (updated show_menu with option 5 and wired options 1-2)
```

### Pattern 1: TSV Rename (RENAME-01, RENAME-02)

**What:** Read rename_plan.tsv line by line; move each `old_path` to `new_path` via `Executor.move()`.
**When to use:** Option 2 in menu.

Ground truth: `Ordenar.ps1` lines 122-161 and `Renombrar.ps1` lines 41-59. The PS1 uses `-LiteralPath` throughout — Python equivalent is constructing `Path(row['old_path'])` without any glob expansion.

```python
# Source: Ordenar.ps1 lines 122-161 (translated to Python)
# Source: CLAUDE.md — csv.DictReader with delimiter='\t', newline='', encoding='utf-8-sig'

import csv
from pathlib import Path

def apply_renames(executor, drive_root: Path) -> dict:
    """Apply renames from rename_plan.tsv. Returns summary counter."""
    plan_file = drive_root / "_organizer_logs" / "rename_plan.tsv"
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}

    if not plan_file.exists():
        print(f"No se encontro rename_plan.tsv en {drive_root}. "
              "Coloca el archivo y vuelve a intentarlo.")
        return counts

    with open(plan_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    if not rows:
        print("El archivo rename_plan.tsv esta vacio. "
              "Agrega entradas y vuelve a intentarlo.")
        return counts

    for i, row in enumerate(rows, 1):
        old_str = (row.get("old_path") or "").strip()
        new_str = (row.get("new_path") or "").strip()

        if not old_str or not new_str:
            logger.warning("Fila %d ignorada: faltan columnas old_path / new_path.", i)
            continue

        counts["procesados"] += 1
        src = Path(old_str)   # literal — no glob expansion

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

    return counts
```

**Critical:** `Path(old_str)` never calls any glob API. Bracket characters in `old_str` are passed as literal path strings to the OS — this is the Python equivalent of PowerShell's `-LiteralPath`. [VERIFIED: Ordenar.ps1 line 138 uses `Test-Path -LiteralPath $old`]

### Pattern 2: Regex Patterns for Series and Movies

**What:** Compile two patterns at module level — one for series (ORG-01), one for movies (ORG-02).
**When to use:** Inside `organize_videos_and_games()` during video classification.

Ground truth: `Ordenar.ps1` lines 236 and 278. Direct translation:

```python
# Source: Ordenar.ps1 line 236 (series) and line 278 (movies)
# Compiled at module level — never inside a loop (CLAUDE.md: re.compile at module level)

RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)

RE_MOVIE = re.compile(
    r"^(?P<title>.+?)\s\((?P<year>(?:19|20)\d{2})\)",
    re.IGNORECASE,
)
```

**Series path construction** (ORG-01):
```python
m = RE_SERIES.match(stem)
if m:
    show = m.group("show").strip()
    season = int(m.group("season"))
    dst_dir = drive_root / "Series" / show / f"Temporada {season}"
    dst = dst_dir / file_path.name
```

**Movie path construction** (ORG-02):
```python
m = RE_MOVIE.match(stem)
if m:
    folder_name = f"{m.group('title').strip()} ({m.group('year')})"
else:
    folder_name = stem.strip()  # fallback: use full stem
dst_dir = drive_root / "Peliculas" / folder_name
dst = dst_dir / file_path.name
```

[VERIFIED: Ordenar.ps1 lines 236-270 (series) and 278-309 (movies)]

### Pattern 3: Recursive Video Scanner with Exclusions

**What:** Walk the drive recursively using `os.scandir`, skip excluded top-level directories.
**When to use:** Entry point for ORG-01 and ORG-02 discovery.

```python
# Source: INFRA-05 (os.scandir only — never glob/rglob for bracket-safe traversal)
# Source: Ordenar.ps1 lines 207-229 (excludeDirs pattern)

VIDEO_EXTS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".mpg", ".mpeg", ".ts",
})

SUB_EXTS: tuple[str, ...] = (".srt", ".ass", ".sub", ".idx")

# Top-level folder names to skip during organize scan (Claude's discretion — confirmed in UI-SPEC)
SCAN_EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "_organizer_logs", "series", "peliculas", "juegos",
})

def _scan_videos_recursive(root: Path, exclude_roots: frozenset[str]) -> list[Path]:
    """Return all video files under root, skipping excluded top-level dirs.

    Uses os.scandir (INFRA-05 — never glob/rglob; handles bracket chars in filenames).
    exclude_roots: lowercased folder names to skip at root level only.
    """
    results = []
    _walk(root, root, exclude_roots, results)
    return results

def _walk(drive_root: Path, current: Path, exclude_roots: frozenset[str], acc: list) -> None:
    try:
        with os.scandir(current) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    # Only apply exclusions at the drive root level
                    if current == drive_root and entry.name.lower() in exclude_roots:
                        continue
                    if should_skip_path(entry.path):
                        continue
                    _walk(drive_root, Path(entry.path), exclude_roots, acc)
                elif entry.is_file(follow_symlinks=False):
                    p = Path(entry.path)
                    if p.suffix.lower() in VIDEO_EXTS:
                        acc.append(p)
    except PermissionError:
        logger.warning("SKIP (permiso denegado): %s", current)
```

**Why top-level exclusion only:** `Ordenar.ps1` uses `Is-ExcludedDir` which checks if the path *starts with* an excluded dir (line 229: `$fullPath -like "$d*"`). This means only subtrees rooted at the excluded dirs are skipped, not random occurrences of the name deep in the tree. The Python equivalent: compare `current == drive_root` before checking the folder name.

### Pattern 4: Game Console Reorganization (ORG-03)

**What:** For each console system folder at drive root, move its contents (not the folder itself) into `Juegos\<system>\`.
**When to use:** Part of `organize_videos_and_games()`, runs before video scan.

Ground truth: `Ordenar.ps1` lines 167-192.

```python
# Source: Ordenar.ps1 lines 167-192
# D-04: PC and Steam excluded — silent skip, no warning

CONSOLE_SYSTEMS: tuple[str, ...] = ("PS1", "PS2", "PSP", "GBA", "GBC")
# PC and Steam intentionally absent — D-04 locked decision

def _organize_games(executor, drive_root: Path, counts: dict) -> None:
    juegos_root = drive_root / "Juegos"
    for sys_name in CONSOLE_SYSTEMS:
        src_dir = drive_root / sys_name
        if not src_dir.exists():
            continue
        dst_dir = juegos_root / sys_name
        try:
            with os.scandir(src_dir) as it:
                for entry in it:
                    counts["procesados"] += 1
                    result = executor.move(Path(entry.path), dst_dir / entry.name)
                    if result is not None:
                        counts["movidos"] += 1
                    else:
                        counts["errores"] += 1
        except PermissionError:
            logger.warning("SKIP (permiso denegado): %s", src_dir)
```

**Note:** Move *contents* of `PS1\`, not the folder itself. This matches PS1 ground truth (`Get-ChildItem -LiteralPath $src | Move-Item`). The folder `PS1\` may remain empty after moving — `_remove_empty_dirs()` will clean it up.

### Pattern 5: Subtitle Co-location (ORG-04)

**What:** After moving a video file, check for same-basename subtitle files in the original source directory and move them to the same destination directory.
**When to use:** Immediately after each successful video move.

Ground truth: `Ordenar.ps1` lines 256-268 and 296-309.

```python
# Source: Ordenar.ps1 lines 256-268 (series subs) and 296-309 (movie subs)

def _move_subtitles(executor, video_src: Path, video_dst_dir: Path, counts: dict) -> None:
    """Move subtitle files sharing video_src's basename to video_dst_dir."""
    stem = video_src.stem
    src_dir = video_src.parent
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

**Calling convention:**
```python
result = executor.move(video_path, dst)
if result is not None:
    counts["movidos"] += 1
    _move_subtitles(executor, video_path, result.parent, counts)
else:
    counts["errores"] += 1
```

### Pattern 6: Empty Folder Cleanup (ORG-05)

**What:** After organize completes, remove all empty directories under drive root (bottom-up).
**When to use:** After `_organize_games()` and the video scan+move loop complete.

```python
# Source: REQUIREMENTS.md ORG-05 — os.rmdir (never shutil.rmtree)
# Bottom-up: walk deepest dirs first so parent becomes empty after child removed

CLEANUP_EXCLUDE_NAMES: frozenset[str] = frozenset({
    "_organizer_logs",  # never touch log dir
})

def _remove_empty_dirs(root: Path, counts_removed: list) -> None:
    """Remove empty directories under root (bottom-up). Never removes root itself."""
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except PermissionError:
        return

    for entry in entries:
        if entry.is_dir(follow_symlinks=False):
            if entry.name.lower() in CLEANUP_EXCLUDE_NAMES:
                continue
            child = Path(entry.path)
            _remove_empty_dirs(child, counts_removed)  # recurse first (bottom-up)
            try:
                child.rmdir()  # only succeeds if empty
                counts_removed.append(child)
                logger.debug("RMDIR: %s", child)
            except OSError:
                pass  # not empty or permission error — skip silently
```

**Why `os.rmdir` / `Path.rmdir()`:** `os.rmdir` (and its pathlib wrapper `Path.rmdir()`) only removes a directory if it is empty — it raises `OSError` otherwise. This is the safe contract. `shutil.rmtree` is explicitly forbidden by REQUIREMENTS.md ORG-05 and the Out-of-Scope table.

### Pattern 7: Dry-run Toggle in Menu (MENU-02)

**What:** Option 5 flips `executor.dry_run` and falls through to menu reprint.
**When to use:** `show_menu()` update.

```python
# Source: 02-CONTEXT.md D-01, 02-UI-SPEC.md Menu Layout Contract

def show_menu(executor: Executor, drive: dict) -> None:
    while True:
        dry_label = "ON" if executor.dry_run else "OFF"
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar videos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir ultima operacion")
        print("  4) Detectar incoherencias")
        print(f"  5) Dry-run: {dry_label}")
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
            executor.dry_run = not executor.dry_run  # D-01: toggle; no output
        else:
            print("Opcion invalida.")


def _print_summary(counts: dict) -> None:
    """MENU-03: one-line summary printed to stdout (not logger)."""
    p = counts.get("procesados", 0)
    m = counts.get("movidos", 0)
    s = counts.get("saltados", 0)
    e = counts.get("errores", 0)
    print(f"\u2713 Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")
```

[VERIFIED: 02-UI-SPEC.md — `✓` prefix always present, field order fixed, single print() call]

### Anti-Patterns to Avoid

- **glob / rglob for file discovery:** Silently skips files with `[` or `]` in their names (INFRA-05). Always use `os.scandir` with a recursive helper.
- **Path.rename() for moves:** Fails across filesystems. Always use `shutil.move(str(src), str(dst))` via `Executor.move()`.
- **shutil.rmtree for cleanup:** Destroys non-empty directories. Only `os.rmdir` / `Path.rmdir()` for ORG-05.
- **Bypassing Executor.move():** Call sites MUST NOT call `shutil.move()` directly — safety guards live in `Executor.move()` only.
- **Top-down empty-folder removal:** Walking top-down means parent still has children when visited. Must walk bottom-up (recurse into children before trying to remove parent).
- **print() for per-file feedback:** All per-file feedback goes through `logger`. Only `_print_summary()` and error messages for missing TSV use `print()` (UI-SPEC.md contract).
- **Re-scanning already-organized destinations:** The video scanner must exclude `Series\`, `Peliculas\`, `Juegos\` from traversal. Omitting exclusions causes double-moves on the second run.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab-separated file parsing | `line.split('\t')` | `csv.DictReader(delimiter='\t')` | split breaks on quoted fields; DictReader handles BOM, quoting, encoding |
| Collision-safe rename | custom suffix logic | `_free_path()` already in organizer.py | Already implemented, tested, correct |
| Cross-filesystem file move | `Path.rename()` | `Executor.move()` → `shutil.move()` | Path.rename fails on different filesystems |
| Directory creation | `os.makedirs` at call sites | `Executor.ensure_dir()` | Already implemented; respects dry_run |
| ROM/ISO + system path guards | inline checks in each function | `Executor.move()` | Safety enforced at single point — never duplicate |

---

## Runtime State Inventory

> This is a pure code-addition phase (no rename, no refactor, no migration). No runtime state is affected.

None — verified: Phase 2 adds new functions to `organizer.py`. It does not rename any existing symbol, move any file at the source-code level, or change any persistent config. No database records, OS registrations, or external service configs are involved.

---

## Common Pitfalls

### Pitfall 1: Double-Move on Second Run
**What goes wrong:** Video files already in `Series\` or `Peliculas\` get re-scanned and moved again (into `Series\Series\Show\...`).
**Why it happens:** Scanner doesn't exclude already-organized destination folders.
**How to avoid:** Check `current == drive_root and entry.name.lower() in SCAN_EXCLUDE_DIR_NAMES` before recursing into top-level dirs. `SCAN_EXCLUDE_DIR_NAMES` must include `"series"`, `"peliculas"`, `"juegos"`.
**Warning signs:** Destination path contains `Series\Series\` or `Peliculas\Peliculas\`.

### Pitfall 2: Game Folder Move vs. Content Move
**What goes wrong:** Moving `PS1\` folder itself (not its contents) results in `Juegos\PS1\PS1\...`.
**Why it happens:** `Executor.move(src_dir, dst_dir)` on a directory moves the whole folder; need to move contents.
**How to avoid:** `os.scandir(src_dir)` and call `Executor.move(entry_path, dst_dir / entry.name)` for each item.
**Warning signs:** `Juegos\PS1\PS1\` exists in output.

### Pitfall 3: Subtitle Move After Failed Video Move
**What goes wrong:** Subtitle is moved but corresponding video was not (blocked or errored). Subtitle ends up orphaned at destination.
**Why it happens:** Subtitle move called regardless of video move result.
**How to avoid:** Only call `_move_subtitles()` when `executor.move()` returns a non-None result.

### Pitfall 4: TSV With BOM from Excel
**What goes wrong:** First column key reads as `'\ufeffold_path'` instead of `'old_path'` — `row.get('old_path')` returns None for all rows.
**Why it happens:** Excel saves TSV with UTF-8 BOM. `encoding='utf-8'` does not strip it.
**How to avoid:** Always use `encoding='utf-8-sig'` when opening the TSV file. [VERIFIED: CLAUDE.md tech stack table]

### Pitfall 5: Top-Down Empty Folder Removal
**What goes wrong:** Parent directory is visited before its children; `os.rmdir` fails because children still exist. No cleanup happens.
**Why it happens:** `os.scandir`-based traversal visits directories in filesystem order (not bottom-up).
**How to avoid:** Recurse into each subdirectory before attempting `rmdir` on it.

### Pitfall 6: Bracket Characters in Rename TSV Paths
**What goes wrong:** `Path('[Show Name]')` constructed correctly, but if any intermediate code expands it via glob, files are silently skipped.
**Why it happens:** Accidental use of `glob.glob()` or `Path.glob()` somewhere in the call chain.
**How to avoid:** Never call any glob API in Phase 2. `Path(old_str)` is safe — it's just string → Path, no filesystem query.

### Pitfall 7: os.rmdir on Non-Empty Folder (silent failure mask)
**What goes wrong:** Overly broad `except OSError: pass` masks actual errors (e.g., permission denied on non-empty dir).
**Why it happens:** Both "not empty" and "permission denied" raise OSError.
**How to avoid:** This is acceptable for Phase 2 — the contract is best-effort cleanup. Log at DEBUG, not ERROR, for failed rmdir attempts. The user is not harmed; files are never deleted.

### Pitfall 8: ASCII-Only Print Strings
**What goes wrong:** `print("✓ Procesados:")` triggers `UnicodeEncodeError` on Windows cmd with cp1252 code page.
**Why it happens:** Windows console default encoding is cp1252 on some locales; `✓` is U+2713, not in cp1252.
**How to avoid:** Two options: (a) use `print(f"\u2713 ...")` (escape sequence, safe in source file) or (b) wrap with `sys.stdout.reconfigure(encoding='utf-8')` once at startup. The `\u2713` escape is the simpler, zero-risk option — it was already decided in 02-UI-SPEC.md (`✓` as accent for success one-liner).
**Note:** Phase 1 established the pattern of using plain ASCII in interactive print() strings for this exact reason. The summary line with `✓` is the only exception — use `\u2713` escape.

---

## Code Examples

### Full organize_videos_and_games() structure

```python
# Source: Ordenar.ps1 lines 167-310 (reorganized into Python functions)

def organize_videos_and_games(executor, drive_root: Path) -> dict:
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)

    # Step 1: Game console folders (ORG-03)
    _organize_games(executor, drive_root, counts)

    # Step 2: Scan all remaining videos (ORG-01, ORG-02)
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
            show = m_series.group("show").strip()
            season = int(m_series.group("season"))
            dst_dir = drive_root / "Series" / show / f"Temporada {season}"
        else:
            m_movie = RE_MOVIE.match(stem)
            if m_movie:
                folder = f"{m_movie.group('title').strip()} ({m_movie.group('year')})"
            else:
                folder = stem.strip()
            dst_dir = drive_root / "Peliculas" / folder

        result = executor.move(video_path, dst_dir / video_path.name)
        if result is not None:
            counts["movidos"] += 1
            _move_subtitles(executor, video_path, result.parent, counts)
        else:
            counts["errores"] += 1

    # Step 3: Remove empty dirs (ORG-05)
    removed = []
    _remove_empty_dirs(drive_root, removed)

    return counts
```

### TSV row validation

```python
# Source: Ordenar.ps1 lines 127-137 (null check + no-exist check)
for i, row in enumerate(rows, 1):
    old_str = (row.get("old_path") or "").strip()
    new_str = (row.get("new_path") or "").strip()
    if not old_str or not new_str:
        logger.warning("Fila %d ignorada: faltan columnas old_path / new_path.", i)
        continue
    src = Path(old_str)
    if not src.exists():
        logger.warning("SKIP (no existe): %s", src)
        counts["saltados"] += 1
        continue
    # ... call executor.move
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PowerShell Rename-Item -Path | Python Path(old_str) + Executor.move | Phase 2 | Path() never glob-expands; safe for brackets |
| PowerShell Get-ChildItem -Recurse | Python os.scandir recursive helper | Phase 2 | Handles bracket chars in filenames |
| PowerShell Out-File append | Python logging.RotatingFileHandler | Phase 1 | Rotation, level filtering, thread safety |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Subtitle move checks same directory as video source (not recursively) | Pattern 5 | Subtitles in subdirs of source would be missed — but this matches Ordenar.ps1 ground truth exactly (same-dir check only) |
| A2 | Movie fallback: if no year detected, use full stem as folder name | Pattern 2 | Files without year pattern land in `Peliculas\<full stem>\` — matches Ordenar.ps1 line 275 (`$movieFolderName = $baseName.Trim()`) |
| A3 | `_remove_empty_dirs` skips `_organizer_logs` only (not Series/Peliculas/Juegos) | Pattern 6 | Newly-empty top-level dirs (e.g. old PS1\) are cleaned — this is correct behavior |

All three assumptions are grounded in `Ordenar.ps1` ground truth. Risk is LOW.

---

## Open Questions

1. **Windows console encoding for ✓ character**
   - What we know: Phase 1 dropped accented chars from print() for cp1252 compatibility. The `✓` (U+2713) summary line is in 02-UI-SPEC.md.
   - What's unclear: Whether the target machine's `sys.stdout.encoding` is cp1252 or utf-8.
   - Recommendation: Use `\u2713` escape in source; add `errors='replace'` to stdout reconfigure if encoding errors appear. Low risk — the character is in the BMP and many terminals handle it.

2. **Empty-dir cleanup scope: drive root vs. subtrees only**
   - What we know: ORG-05 says "tras organizar, carpetas vacias se eliminan".
   - What's unclear: Should the cleanup visit the entire drive or only the folders that were modified (Series\, Peliculas\, Juegos\, and original console dirs)?
   - Recommendation: Entire drive root — matches Ordenar.ps1 implicit behavior (no cleanup step exists in PS1 so there is no ground truth). Scanning the whole drive is safe because `os.rmdir` only removes empty folders.

---

## Environment Availability

> Phase 2 is pure Python stdlib additions to organizer.py. No external tools, services, or CLI utilities are required beyond what Phase 1 already verified.

Step 2.6: SKIPPED (no new external dependencies — all Phase 2 operations use stdlib modules already imported in Phase 1)

---

## Validation Architecture

> `nyquist_validation` is `false` in `.planning/config.json` — validation section skipped per protocol.

---

## Security Domain

> This is a local tool that operates only on the user-selected removable drive. No network access, no authentication, no user-supplied code execution. ASVS categories do not apply to this threat model.

Key safety controls already in place:
- `is_no_touch()` — hard block on ROM/ISO extensions (INFRA-03) [VERIFIED: organizer.py line 85]
- `should_skip_path()` — hard block on system paths (INFRA-04) [VERIFIED: organizer.py line 92]
- `_free_path()` — prevents overwrites (INFRA-07) [VERIFIED: organizer.py line 100]
- `os.rmdir` only — prevents accidental mass deletion (ORG-05 requirement)

---

## Sources

### Primary (HIGH confidence)

- `Ordenar.ps1` (project root) — ground-truth regex patterns (lines 236, 278), game folder logic (lines 167-192), scan exclusions (lines 207-229), subtitle co-location (lines 256-268, 296-309)
- `organizer.py` (project root, Phase 1) — existing Executor API, established patterns
- `02-CONTEXT.md` — locked decisions D-01 through D-05 and discretion areas
- `02-UI-SPEC.md` — exact menu layout, summary format, copywriting, scan exclusion contract
- `CLAUDE.md` — tech stack table, stdlib-only constraint, csv encoding guidance
- `01-PATTERNS.md` — Phase 1 established patterns (os.scandir, shutil.move, logging call pattern)

### Secondary (MEDIUM confidence)

- `Renombrar.ps1` (project root) — TSV reading pattern (lines 41-59); confirms absolute paths and -LiteralPath semantics

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, all already imported in Phase 1
- Architecture: HIGH — direct translation from verified PS1 ground truth + Phase 1 patterns
- Pitfalls: HIGH — extracted from actual PS1 code and Phase 1 learnings (e.g. encoding pitfall lived through in Phase 1)
- Regex patterns: HIGH — copied directly from Ordenar.ps1 lines 236 and 278

**Research date:** 2026-04-19
**Valid until:** Stable — pure stdlib, no external dependencies to track

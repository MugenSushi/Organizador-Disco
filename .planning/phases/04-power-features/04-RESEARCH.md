# Phase 4: Power Features - Research

**Researched:** 2026-04-21
**Domain:** Python stdlib — regex pattern matching, file scanning, TSV generation, text reporting
**Confidence:** HIGH

## Summary

Phase 4 adds two read-only intelligence features to the organizer: (1) a rename plan generator that scans the drive and proposes TSV normalizations for malformed series, movie, and misplaced game files; (2) a coherence checker that audits the drive structure and produces a human-readable report without moving anything.

Both features are built entirely from existing stdlib and project infrastructure. No new libraries are required. The rename generator reuses `_scan_videos_recursive()`, `RE_SERIES`, `RE_MOVIE`, `is_no_touch()`, `should_skip_path()`, and the established TSV format from `apply_renames()`. The coherence checker is also a scan-and-report function using the same scanner, with string normalization applied during comparison.

The main integration points are: replacing the `print("(Disponible en Fase 4)")` stub in `show_menu()` with the real coherence checker call, and adding option 6 for the rename generator. Both new functions belong in a new SECTION 16 in `organizer.py` following the established section pattern.

**Primary recommendation:** Implement SECTION 16 with four functions: `generate_rename_plan()`, `_propose_series_rename()`, `_propose_movie_rename()`, and `check_coherence()`. Wire them into `show_menu()` at options 4 and 6. Write output files to `_organizer_logs\` using UTF-8 encoding consistent with existing log infrastructure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Generator detects three file categories: (1) series with recognizable structure but wrong format, (2) movies with title+year but wrong format, (3) console game files outside `Juegos\<system>\`.
- **D-02:** Generator only normalizes what it fully recognizes — if a file lacks sufficient structure (show+season+episode for series, title+year for movies), it is skipped entirely. Zero placeholders, zero false positives.
- **D-03:** TSV is saved to `_organizer_logs\rename_plan.tsv` (same path as `apply_renames()`). Never auto-applied — user reviews and uses option 2 to apply.
- **D-04:** Generator goes in menu option 6. Menu order: 1) Organizar, 2) Aplicar rename, 3) Revertir, 4) Detectar incoherencias, 5) Dry-run toggle, 6) Generar rename_plan.tsv, 0) Salir.
- **D-05:** Coherence report is output-only — never moves files. Detects: (a) videos outside Series\/Peliculas\, (b) series episodes without a season folder, (c) duplicate titles after name normalization.

### Claude's Discretion

- **Format of coherence report output** — Print to console AND write to `_organizer_logs\coherence_report.txt`. Claude decides exact line format.
- **Normalization algorithm for duplicates (COH-03)** — Strip year (in parentheses), strip resolution tags (1080p, 720p, 4K, x264, x265, BluRay, HDRip, WEBRip, etc.), lowercase, strip extra spaces. Exact-match on normalized result.
- **Additional variant patterns for generator (D-01 variants)** — Claude decides which separator/format variants to detect for series and movies (e.g., underscores, dots as separators).
- **Internal structure of SECTION 16** — Claude organizes the Phase 4 functions in `organizer.py` following the established section pattern.

### Deferred Ideas (OUT OF SCOPE)

- **SxxExx as primary pattern (V2-01)** — Extending pattern support beyond normalizing to canonical format belongs to v2.
- No other scope deviations occurred during discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RENAME-03 | Script can auto-generate a `rename_plan.tsv` by scanning the drive for malformed names | Regex variant detection, `_scan_videos_recursive` reuse, TSV writing via `csv.writer` |
| RENAME-04 | Generated TSV saved to `_organizer_logs\` for user review; never auto-applied | Output path convention from `LOG_DIR_NAME` constant; file write pattern from existing log infrastructure |
| COH-01 | Scan and report video files outside expected folders (Series, Peliculas) | Path prefix check against `drive_root / "Series"` and `drive_root / "Peliculas"` |
| COH-02 | Report series episodes without an assigned season folder | Detect video files under a show folder that sit directly under `Series\<show>\` without a `Temporada X` intermediate directory |
| COH-03 | Report duplicate titles after name normalization (strip year, resolution tags, etc.) | Strip-normalize stem → group by normalized key → report groups with count > 1 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rename plan generation | Single-file script (organizer.py SECTION 16) | — | Scan-and-write operation; no network, no separate process |
| TSV output | organizer.py file writer | `_organizer_logs\` directory (already managed) | Consistent with how `apply_renames()` reads the same file |
| Coherence report (console) | organizer.py print() | — | Interactive output; same pattern as `_print_summary()` |
| Coherence report (file) | organizer.py file writer | `_organizer_logs\` directory | Persistent audit trail, especially useful for large drives |
| Menu integration | show_menu() in organizer.py | — | Follows established `while True` / `input()` menu loop |

## Standard Stack

### Core (all stdlib, zero new installs)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `re` | stdlib | Compile variant patterns for series/movie detection | Already used; module-level compile mandatory per CLAUDE.md |
| `csv` | stdlib | Write TSV with `delimiter='\t'`; `csv.writer` for generation | Same module used by `apply_renames()` for reading; `csv.writer` is the symmetric write API |
| `os.scandir` | stdlib | File discovery scan | INFRA-05 lock — never glob/rglob; `_scan_videos_recursive()` already provides this |
| `pathlib.Path` | stdlib | Path construction, parent checks, suffix extraction | Project standard; `/` operator for joining |
| `logging` | stdlib | Log generator and checker events | Named logger `"organizer"` already configured |

### No New Libraries

This phase adds zero new imports. All required functionality is already present in the codebase.

**Installation:** None required.

## Architecture Patterns

### System Architecture Diagram

```
drive_root/
│
├── [scan via _scan_videos_recursive()]
│       │
│       ├─► video files (VIDEO_EXTS)
│       │        │
│       │        ├─► generate_rename_plan()
│       │        │       ├─► _propose_series_rename()   → detect variant series names
│       │        │       ├─► _propose_movie_rename()    → detect variant movie names
│       │        │       └─► game file detector         → detect game files outside Juegos\
│       │        │                   │
│       │        │                   └─► rows: [{old_path, new_path}]
│       │        │                               │
│       │        │                               └─► csv.writer → _organizer_logs\rename_plan.tsv
│       │        │
│       │        └─► check_coherence()
│       │               ├─► COH-01: path prefix check → not under Series\ or Peliculas\
│       │               ├─► COH-02: season folder check → RE_SERIES match, parent.name check
│       │               └─► COH-03: normalize stem → group by key → find count > 1
│       │                               │
│       │                               └─► print() to console
│       │                               └─► write → _organizer_logs\coherence_report.txt
│       │
│       └── [skipped] is_no_touch() / should_skip_path() guards applied first
```

### Recommended Project Structure

No new files or directories. All new code goes into `organizer.py` as SECTION 16, following the established section pattern. Output files go into the existing `_organizer_logs\` directory.

```
organizer.py
  ...existing sections 1-15...
  SECTION 16 — Power features (Phase 4)
    generate_rename_plan(drive_root)
    _propose_series_rename(stem, path, drive_root) -> tuple | None
    _propose_movie_rename(stem, path, drive_root) -> tuple | None
    check_coherence(drive_root)
    _normalize_for_dedup(stem) -> str
```

### Pattern 1: Rename Plan Generator

**What:** Scan all video files + game-extension files, apply variant-format detection, produce (old_path, new_path) rows, write TSV.

**When to use:** Called from `show_menu()` option 6.

**TSV writing — symmetric with apply_renames() reading:**
```python
# Source: csv module docs + existing apply_renames() pattern in organizer.py
import csv
from pathlib import Path

def generate_rename_plan(drive_root: Path) -> dict:
    """Scan drive and write rename_plan.tsv with proposed normalizations. (RENAME-03, RENAME-04)"""
    out_path = drive_root / LOG_DIR_NAME / "rename_plan.tsv"
    rows = []

    # Scan video files
    video_files = _scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)
    for p in video_files:
        proposal = _propose_series_rename(p.stem, p, drive_root)
        if proposal is None:
            proposal = _propose_movie_rename(p.stem, p, drive_root)
        if proposal:
            rows.append(proposal)

    # Scan for misplaced game files (outside Juegos\)
    juegos_root = drive_root / "Juegos"
    for sys_name in CONSOLE_SYSTEMS:
        sys_dir = drive_root / sys_name
        # sys_dir itself is the misplaced location — contents should be in Juegos\sys_name\
        if sys_dir.exists():
            try:
                with os.scandir(sys_dir) as it:
                    for entry in it:
                        if entry.is_file(follow_symlinks=False):
                            p = Path(entry.path)
                            if is_no_touch(str(p)) or should_skip_path(str(p)):
                                continue
                            dst = juegos_root / sys_name / p.name
                            rows.append((str(p), str(dst)))
            except PermissionError:
                logger.warning("SKIP (permiso denegado): %s", sys_dir)

    counts = {"propuestos": len(rows), "escritos": 0}
    if not rows:
        print("No se encontraron archivos para renombrar.")
        return counts

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["old_path", "new_path"])  # header
        for old, new in rows:
            writer.writerow([old, new])
    counts["escritos"] = len(rows)
    print(f"rename_plan.tsv generado: {len(rows)} propuestas -> {out_path}")
    return counts
```

**Key constraint:** Output uses `encoding="utf-8-sig"` (same BOM as what `apply_renames()` reads with `utf-8-sig`) so the file round-trips cleanly if opened in Excel and re-saved. [VERIFIED: existing apply_renames() uses utf-8-sig]

### Pattern 2: Series Variant Detection

**What:** Detect video filenames that represent a series episode in a variant format and produce the canonical form.

**Canonical form (target):** `Show - Temporada X - Episodio Y.ext`

**Variant formats to detect (Claude's Discretion):**

| Format | Example | Regex strategy |
|--------|---------|----------------|
| Underscores as separators | `Show_Name_Temporada_1_Episodio_5.mkv` | Normalize underscores to spaces before matching |
| Dots as separators | `Show.Name.Temporada.1.Episodio.5.mkv` | Normalize dots to spaces before matching |
| SxxExx suffix (partial) | `Show Name S01E05.mkv` | Detect SxxExx, extract numbers, produce canonical; only if show name is clearly inferrable |
| Already-canonical | `Show - Temporada 1 - Episodio 5.mkv` | RE_SERIES matches → skip (file is already correct) |

**Decision on SxxExx (from CONTEXT.md specifics):** If SxxExx is found AND the show name is clearly before it (non-empty prefix), convert to canonical. If show name cannot be inferred, skip per D-02.

```python
# Compiled at module level (CLAUDE.md convention)
# Variant 1: underscores/dots as separators, Spanish keywords
RE_SERIES_VARIANT = re.compile(
    r"^(?P<show>.+?)[_.\s]+[Tt]emporada[_.\s]+(?P<season>\d+)[_.\s]+[Ee]pisodio[_.\s]+(?P<ep>\d+)",
    re.IGNORECASE,
)

# Variant 2: SxxExx format
RE_SERIES_SXXEXX = re.compile(
    r"^(?P<show>.+?)[_.\s]+[Ss](?P<season>\d{1,2})[Ee](?P<ep>\d{1,3})",
    re.IGNORECASE,
)

def _propose_series_rename(stem: str, path: Path, drive_root: Path):
    """Return (old_path_str, new_path_str) if stem is a series in variant format, else None."""
    # If already canonical, skip
    if RE_SERIES.match(stem):
        return None

    m = RE_SERIES_VARIANT.match(stem)
    if not m:
        m = RE_SERIES_SXXEXX.match(stem)

    if not m:
        return None

    show = re.sub(r"[_.]", " ", m.group("show")).strip()
    season = int(m.group("season"))
    ep = int(m.group("ep"))

    if not show:  # D-02: can't infer show name → skip
        return None

    canonical = f"{show} - Temporada {season} - Episodio {ep}{path.suffix}"
    new_path = path.parent / canonical
    return (str(path), str(new_path))
```

### Pattern 3: Movie Variant Detection

**What:** Detect video filenames representing movies in variant format (resolution tags, extra metadata appended) and propose clean canonical form `Title (Year).ext`.

```python
# Compiled at module level
# Matches title + year anywhere in stem, with trailing garbage
RE_MOVIE_VARIANT = re.compile(
    r"^(?P<title>.+?)[_.\s]+\(?(?P<year>(?:19|20)\d{2})\)?",
    re.IGNORECASE,
)

def _propose_movie_rename(stem: str, path: Path, drive_root: Path):
    """Return (old_path_str, new_path_str) if stem is a movie in variant format, else None."""
    # If already canonical, skip
    if RE_MOVIE.match(stem):
        return None

    m = RE_MOVIE_VARIANT.match(stem)
    if not m:
        return None

    title = re.sub(r"[_.]", " ", m.group("title")).strip()
    year = m.group("year")

    if not title:  # D-02: can't infer title → skip
        return None

    canonical = f"{title} ({year}){path.suffix}"
    new_path = path.parent / canonical
    # Only propose if name actually changes
    if new_path.name == path.name:
        return None
    return (str(path), str(new_path))
```

### Pattern 4: Coherence Checker

**What:** Scan drive, classify findings into three categories (COH-01, COH-02, COH-03), print to console and write to file.

```python
# Normalization tags for COH-03 duplicate detection (Claude's Discretion)
RE_NORM_STRIP = re.compile(
    r"\b(?:1080p|720p|480p|4[Kk]|2160p|x264|x265|h264|h265|avc|hevc"
    r"|bluray|blu-ray|bdrip|brrip|hdrip|webrip|web-dl|dvdrip|xvid"
    r"|hdr|sdr|dts|ac3|aac|mp3)\b",
    re.IGNORECASE,
)

def _normalize_for_dedup(stem: str) -> str:
    """Strip year, resolution/codec tags, lowercase, collapse spaces. (COH-03 Claude's Discretion)"""
    s = stem
    s = re.sub(r"\((?:19|20)\d{2}\)", "", s)   # strip (year)
    s = RE_NORM_STRIP.sub("", s)
    s = re.sub(r"[_.\-]+", " ", s)              # normalize separators
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def check_coherence(drive_root: Path) -> None:
    """Audit drive structure and report problems. (COH-01, COH-02, COH-03)"""
    series_root   = drive_root / "Series"
    peliculas_root = drive_root / "Peliculas"
    report_path   = drive_root / LOG_DIR_NAME / "coherence_report.txt"

    lines = []

    # COH-01: video files outside Series\ and Peliculas\
    outside = []
    all_videos = _scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)
    for p in all_videos:
        p_str = str(p).lower()
        if not (p_str.startswith(str(series_root).lower()) or
                p_str.startswith(str(peliculas_root).lower())):
            outside.append(p)

    lines.append(f"=== COH-01: Videos fuera de Series\\ y Peliculas\\ ({len(outside)}) ===")
    for p in outside:
        lines.append(f"  {p}")

    # COH-02: series episodes directly under Series\<show>\ without Temporada X subfolder
    unfoldered = []
    if series_root.exists():
        try:
            with os.scandir(series_root) as it:
                for show_entry in it:
                    if not show_entry.is_dir(follow_symlinks=False):
                        continue
                    show_dir = Path(show_entry.path)
                    try:
                        with os.scandir(show_dir) as show_it:
                            for ep_entry in show_it:
                                if ep_entry.is_file(follow_symlinks=False):
                                    p = Path(ep_entry.path)
                                    if p.suffix.lower() in VIDEO_EXTS:
                                        unfoldered.append(p)
                    except PermissionError:
                        logger.warning("SKIP (permiso): %s", show_dir)
        except PermissionError:
            logger.warning("SKIP (permiso): %s", series_root)

    lines.append(f"\n=== COH-02: Episodios sin carpeta Temporada ({len(unfoldered)}) ===")
    for p in unfoldered:
        lines.append(f"  {p}")

    # COH-03: duplicate titles after normalization
    seen: dict[str, list[Path]] = {}
    for p in all_videos:
        key = _normalize_for_dedup(p.stem)
        if not key:
            continue
        seen.setdefault(key, []).append(p)

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    lines.append(f"\n=== COH-03: Titulos duplicados (normalizados) ({len(duplicates)} grupos) ===")
    for key, paths in sorted(duplicates.items()):
        lines.append(f"  [{key}]")
        for p in paths:
            lines.append(f"    {p}")

    # Output to console
    for line in lines:
        print(line)

    # Output to file
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n[OK] Reporte guardado en: {report_path}")
```

### Pattern 5: Menu Integration

**What:** Replace the option-4 stub and add option 6 in `show_menu()`.

```python
# In show_menu() — replace the stub block and extend the menu print
# Current state (Phase 3 result):
#   elif choice == "4":
#       print("(Disponible en Fase 4)")
# No option 6 exists yet.

# Target state after Phase 4:
print("  4) Detectar incoherencias")
print(f"  5) Dry-run: {dry_label}")
print("  6) Generar rename_plan.tsv")
print("  0) Salir")
# ...
elif choice == "4":
    check_coherence(Path(drive["root"]))
elif choice == "6":
    generate_rename_plan(Path(drive["root"]))
```

Note: options 4 and 6 are read-only operations — they do NOT call `_prepare_executor_for_run()` or `_flush_and_clear()`. The executor is not needed for these features. [VERIFIED: CONTEXT.md D-05 confirms coherence checker never moves files; generator only writes a text file]

### Anti-Patterns to Avoid

- **Calling executor.move() from generate_rename_plan():** Generator ONLY writes the TSV — it never moves files. Moving is option 2's job.
- **Using glob/rglob for scanning:** INFRA-05 lock — always `os.scandir`. The existing `_scan_videos_recursive()` handles this.
- **Regex inside functions:** All new regex patterns (`RE_SERIES_VARIANT`, `RE_SERIES_SXXEXX`, `RE_NORM_STRIP`, `RE_MOVIE_VARIANT`) must be compiled at module level per CLAUDE.md.
- **Auto-applying renames:** The generator writes to `rename_plan.tsv` and stops. It must not call `apply_renames()`.
- **Using print() for log events:** Operational events (SKIP, MATCH) go to `logger`; user-facing output (summaries, report) goes to `print()`.
- **Overwriting rename_plan.tsv silently:** The current code in `apply_renames()` does not warn if TSV already exists. The generator overwrites the file — it should note this in the console output so the user knows a previous plan was replaced.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TSV writing | Custom file.write() with tabs | `csv.writer(f, delimiter='\t')` | Handles quoting edge cases (filenames with tabs in theory); symmetric with csv.DictReader used in apply_renames() |
| File discovery | glob, rglob, os.walk | `_scan_videos_recursive()` already implemented | INFRA-05 lock; function already handles exclude_roots, follow_symlinks=False, PermissionError |
| Path joining | string concatenation | `pathlib.Path / operator` | Project standard; avoids Windows separator issues |
| Text normalization | complex multi-step regex built inline | Module-level RE_NORM_STRIP + simple re.sub chain | Compiled once, readable, testable |

**Key insight:** Phase 4 is a consumer of Phase 2-3 infrastructure, not a builder. 80% of the implementation is wiring existing functions together and writing output files.

## Common Pitfalls

### Pitfall 1: Detecting Already-Canonical Files as Rename Candidates
**What goes wrong:** `RE_SERIES_VARIANT` or `RE_MOVIE_VARIANT` could match files that already match the canonical `RE_SERIES` or `RE_MOVIE` patterns, producing a no-op row (old_path == new_path) or a spurious rename.
**Why it happens:** The variant patterns are intentionally broad to catch separator variants.
**How to avoid:** In both `_propose_series_rename()` and `_propose_movie_rename()`, check `RE_SERIES.match(stem)` / `RE_MOVIE.match(stem)` FIRST. If canonical matches, return None immediately. Also guard: if `new_path.name == path.name`, return None.
**Warning signs:** TSV contains rows where old_path and new_path have the same filename.

### Pitfall 2: COH-03 Normalization Produces Empty Keys
**What goes wrong:** Some filenames, after stripping year, tags, separators, reduce to an empty string. Grouping by empty key creates one false mega-group of all unclassifiable files.
**Why it happens:** Filenames that are entirely composed of resolution tags + year (e.g., `1080p (2021).mkv`) normalize to `""`.
**How to avoid:** In `check_coherence()`, skip any file where `_normalize_for_dedup(stem)` returns an empty string.
**Warning signs:** One group in COH-03 containing dozens of unrelated files.

### Pitfall 3: Scanning Series\ for COH-02 Using _scan_videos_recursive()
**What goes wrong:** `_scan_videos_recursive()` with `SCAN_EXCLUDE_DIR_NAMES` excludes "series" from the top-level scan. Using it for the COH-02 scan (which needs to enter Series\) requires a different exclude set or a manual scan.
**Why it happens:** `SCAN_EXCLUDE_DIR_NAMES` contains `"series"` to prevent double-organizing videos that are already in the right place.
**How to avoid:** For COH-02, manually scan `series_root` using `os.scandir` directly (one level for show directories, then one more level to check for episode files at show-root level). Do NOT reuse `_scan_videos_recursive` rooted at `drive_root` for this check — or if reusing it, call it rooted at `series_root` with an empty exclude set.
**Warning signs:** COH-02 always reports zero episodes even when there are unfoldered episodes.

### Pitfall 4: rename_plan.tsv Overwrite Race
**What goes wrong:** If the user has a reviewed-but-not-yet-applied `rename_plan.tsv`, running option 6 silently replaces it.
**Why it happens:** The generator opens the file with mode `"w"` (write, truncate).
**How to avoid:** Before writing, check if `rename_plan.tsv` exists and warn the user: "Se sobreescribira el rename_plan.tsv existente. Continuar? (s/N)". Only if confirmed, write.
**Warning signs:** User loses manually curated TSV.

### Pitfall 5: SxxExx Match Group Named "show" Contains Empty String
**What goes wrong:** A filename like `S01E05.mkv` (no show name prefix) matches `RE_SERIES_SXXEXX` with `show=""`.
**Why it happens:** The `+?` quantifier can match zero characters before `[_.\s]+S01E05`.
**How to avoid:** After extracting `show = m.group("show").strip()`, check `if not show: return None` per D-02.
**Warning signs:** TSV proposals with empty old-path prefix / blank show name in new-path.

### Pitfall 6: COH-01 Path Prefix Check on Windows (Case Sensitivity)
**What goes wrong:** `str(p).startswith(str(series_root))` fails on Windows if drive letter case differs (e.g., `C:` vs `c:`).
**Why it happens:** Windows paths are case-insensitive but Python string comparison is case-sensitive.
**How to avoid:** Normalize both sides to lowercase: `str(p).lower().startswith(str(series_root).lower())`.
**Warning signs:** COH-01 reports all organized videos as "outside" their folders.

## Code Examples

Verified patterns from codebase:

### Existing TSV Reading (apply_renames — organizer.py:282)
```python
# Source: organizer.py SECTION 10 (Phase 2)
with open(plan_file, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter="\t")
    rows = list(reader)
```

### Symmetric TSV Writing (new in Phase 4)
```python
# Symmetric write using csv.writer (the write-side of the same format)
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["old_path", "new_path"])
    for old, new in rows:
        writer.writerow([old, new])
```

### Existing Scanner Reuse (organizer.py:343)
```python
# Source: organizer.py SECTION 11 — reuse as-is for video file discovery
video_files = _scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)
```

### Existing Safety Guards (organizer.py:106-116)
```python
# Source: organizer.py SECTION 5 — apply before any scan processing
if is_no_touch(str(p)) or should_skip_path(str(p)):
    continue
```

### Existing Module-Level Regex Pattern (organizer.py:259-267)
```python
# Source: organizer.py SECTION 9 — model new patterns after this
RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PowerShell scripts ran top-to-bottom, no generation | Python organizer provides interactive menu with read-only audit features | Phase 1-3 | Users can inspect before acting |
| No rename suggestion capability | generate_rename_plan() writes reviewable TSV | Phase 4 | Reduces manual TSV authoring effort |
| No drive audit | check_coherence() produces structured report | Phase 4 | Exposes structural problems without risk |

**No deprecated approaches:** All Phase 4 patterns are new additions with no legacy code to replace.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `RE_SERIES_VARIANT` with broad separator matching will not produce excessive false positives on typical media file names | Pattern 2 | Generator proposes bad renames; user must review TSV anyway per D-03 so impact is limited |
| A2 | `_scan_videos_recursive(series_root, frozenset())` (empty exclude set) is safe to call for COH-02 — no infinite loops or excessive depth on typical drives | Common Pitfalls #3 | Could be slow on pathological directory structures, but not incorrect |
| A3 | Writing coherence report to disk as UTF-8 (no BOM) is appropriate — report is not intended to be opened in Excel | Pattern 4 | If user opens in Excel on some locales, encoding may cause display issues; risk is low for a plain-text report |

## Open Questions

1. **Overwrite confirmation for rename_plan.tsv (Pitfall 4)**
   - What we know: The generator overwrites `rename_plan.tsv` without warning.
   - What's unclear: Whether to silently overwrite (simpler) or prompt (safer). CONTEXT.md does not address this.
   - Recommendation: Add a single-line prompt `"Ya existe rename_plan.tsv. Sobreescribir? [s/N]: "` before writing. Default to N (safe). If user says N, return without writing. This follows the dry-run/safety-first philosophy of the project.

2. **Game file detection scope for the generator**
   - What we know: D-01 category 3 is "game files outside `Juegos\<system>\`". CONTEXT.md Specifics says: files outside `Juegos\<system>\` — those already inside are not reviewed.
   - What's unclear: Whether to detect game files ONLY in the known system folder roots (`drive_root/PS1/`, etc.) or also in arbitrary subdirectories.
   - Recommendation: Only check the known system folder roots (`drive_root / sys_name` for each `sys_name` in `CONSOLE_SYSTEMS`). This is consistent with how `_organize_games()` works in Phase 2 (it moves CONTENTS of `drive_root/PS1/` etc.). Do not recursively hunt for game files in arbitrary locations — that risks false positives per D-02.

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is purely code/config changes within `organizer.py`. No external tools, services, CLIs, or runtimes beyond Python 3.x stdlib are required.

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is omitted.

## Security Domain

Phase 4 adds no new file mutation paths (generator writes only a text file; coherence checker writes only a text file). Both outputs are within `_organizer_logs\` on the user-selected drive. No new attack surface beyond what Phases 1-3 already cover.

The key security property to preserve: `generate_rename_plan()` must NOT call `executor.move()` or any mutation — it is a read-only scanner that writes one TSV file. The planner should verify this in acceptance criteria.

## Sources

### Primary (HIGH confidence)
- `organizer.py` SECTION 9 (RE_SERIES, RE_MOVIE), 10 (apply_renames), 11 (_scan_videos_recursive) — directly read; all interfaces verified [VERIFIED: codebase]
- `CLAUDE.md` — tech stack, module-level regex convention, csv patterns [VERIFIED: codebase]
- `04-CONTEXT.md` — all decisions D-01 through D-05 [VERIFIED: codebase]
- Python docs (csv.writer) — symmetric to csv.DictReader used in apply_renames [ASSUMED — training knowledge; stdlib API is stable]

### Secondary (MEDIUM confidence)
- `01-PATTERNS.md`, `02-01-SUMMARY.md` — established section/function patterns [VERIFIED: codebase]
- `Ordenar.ps1` — ground truth for game systems list and skip patterns [VERIFIED: codebase]

### Tertiary (LOW confidence)
- None — all claims are grounded in the existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new libraries; all patterns already in codebase
- Architecture: HIGH — SECTION 16 pattern is established; functions are new but simple compositions
- Pitfalls: HIGH — most pitfalls derived from direct code inspection of existing functions and locked decisions

**Research date:** 2026-04-21
**Valid until:** Indefinite for this project (stable stdlib, no external dependencies)

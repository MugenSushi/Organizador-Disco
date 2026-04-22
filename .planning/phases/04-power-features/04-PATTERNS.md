# Phase 4: Power Features - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 1 (organizer.py — all new code is added as SECTION 16 plus menu edits in show_menu())
**Analogs found:** 5 / 5 functional units — all patterns have exact codebase analogs

## File Classification

Phase 4 adds no new files. All changes are edits to `organizer.py`.

| Logical Unit | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `generate_rename_plan()` (new function) | scanner + file-writer | batch + file-I/O | `apply_renames()` (lines 272-338) | exact — same TSV format, same path conventions |
| `_propose_series_rename()` (new function) | transform/classifier | batch | `organize_videos_and_games()` regex classify block (lines 481-496) | role-match — same RE_SERIES check-first pattern |
| `_propose_movie_rename()` (new function) | transform/classifier | batch | `organize_videos_and_games()` regex classify block (lines 481-496) | role-match — same RE_MOVIE check-first pattern |
| `check_coherence()` (new function) | scanner + reporter | batch + file-I/O | `_organize_games()` scandir + `undo_last_run()` print summary | partial — scandir pattern exact; dual print+write is new |
| `_normalize_for_dedup()` (new function) | utility/transform | transform | no direct analog — pure string utility | no analog |
| New module-level regex constants (`RE_SERIES_VARIANT`, `RE_SERIES_SXXEXX`, `RE_MOVIE_VARIANT`, `RE_NORM_STRIP`) | config/constants | — | `RE_SERIES` / `RE_MOVIE` (lines 259-267, SECTION 9) | exact |
| `show_menu()` edits — option 4 stub replacement + option 6 addition | controller/menu | request-response | `show_menu()` itself (lines 675-709) | exact |

---

## Pattern Assignments

### `generate_rename_plan(drive_root)` — batch scanner + TSV writer

**Analog:** `apply_renames()` — `organizer.py` lines 272-338

**Imports pattern** — zero new imports needed; all already present at lines 3-14:
```python
import csv
import os
import re
from pathlib import Path
```

**TSV write pattern** — symmetric mirror of the read pattern in `apply_renames()` (lines 282-284):
```python
# READ side (apply_renames, line 282-284):
with open(plan_file, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter="\t")
    rows = list(reader)

# WRITE side (generate_rename_plan — new code must match this exactly):
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["old_path", "new_path"])   # header matches DictReader keys
    for old, new in rows:
        writer.writerow([old, new])
```
Key constraint: `encoding="utf-8-sig"` on both sides so the file round-trips through Excel without BOM corruption.

**Output path convention** — copy from `apply_renames()` line 274:
```python
# apply_renames (line 274):
plan_file = drive_root / "_organizer_logs" / "rename_plan.tsv"

# generate_rename_plan must write to the same path:
out_path = drive_root / LOG_DIR_NAME / "rename_plan.tsv"
# LOG_DIR_NAME = "_organizer_logs"  (line 37)
```

**Scanner reuse pattern** — copy from `organize_videos_and_games()` lines 474-479:
```python
exclude_top = SCAN_EXCLUDE_DIR_NAMES
video_files = _scan_videos_recursive(drive_root, exclude_top)

if not video_files:
    print("No se encontraron archivos de video para organizar.")
    return counts
```

**Game file scan pattern** — copy from `_organize_games()` lines 415-438:
```python
for sys_name in CONSOLE_SYSTEMS:
    src_dir = drive_root / sys_name
    if not src_dir.exists():
        continue
    try:
        with os.scandir(src_dir) as it:
            for entry in it:
                p = Path(entry.path)
                if is_no_touch(str(p)) or should_skip_path(str(p)):
                    continue
                # ... generate proposal row
    except PermissionError:
        logger.warning("SKIP (permiso denegado): %s", src_dir)
```
Difference for the generator: instead of calling `executor.move()`, append `(str(p), str(dst))` to `rows`.

**Overwrite guard** — pattern does NOT exist in codebase yet (pitfall 4 in RESEARCH.md). Implement as:
```python
if out_path.exists():
    ans = input("Ya existe rename_plan.tsv. Sobreescribir? [s/N]: ").strip().lower()
    if ans != "s":
        print("Operacion cancelada.")
        return counts
```

**Summary / return dict pattern** — copy from `apply_renames()` line 275:
```python
counts = {"propuestos": 0, "escritos": 0}
# ... populate
print(f"rename_plan.tsv generado: {len(rows)} propuestas -> {out_path}")
return counts
```

**Error handling pattern** — copy from `_organize_games()` lines 437-438:
```python
except PermissionError:
    logger.warning("SKIP (permiso denegado): %s", src_dir)
```
Operational events (SKIP, MATCH) go to `logger`; user summaries go to `print()`.

---

### `_propose_series_rename(stem, path, drive_root)` — series variant classifier

**Analog:** classify block in `organize_videos_and_games()` — `organizer.py` lines 481-496

**Check-first pattern** — always check canonical regex FIRST, return None on match (lines 485-489):
```python
m_series = RE_SERIES.match(stem)
if m_series:
    # already canonical — this is the guard to copy for _propose_series_rename:
    return None
```

**Group extraction + path construction pattern** — copy from lines 487-489:
```python
show = m_series.group("show").strip()
season = int(m_series.group("season"))
dst_dir = drive_root / "Series" / show / f"Temporada {season}"
```
For the proposal function, construct `new_path` using the same group names:
```python
show = re.sub(r"[_.]", " ", m.group("show")).strip()
season = int(m.group("season"))
ep = int(m.group("ep"))
if not show:          # D-02: skip unresolvable
    return None
canonical = f"{show} - Temporada {season} - Episodio {ep}{path.suffix}"
new_path = path.parent / canonical
return (str(path), str(new_path))
```

**Module-level regex convention** — copy from SECTION 9 (lines 259-267):
```python
RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)
```
New variant patterns follow exactly this structure — compiled at module level in a new SECTION 16 constants block, never inside a function.

---

### `_propose_movie_rename(stem, path, drive_root)` — movie variant classifier

**Analog:** classify block in `organize_videos_and_games()` — `organizer.py` lines 490-495

**Check-first pattern** — same guard as series:
```python
m_movie = RE_MOVIE.match(stem)
if m_movie:
    return None   # already canonical
```

**Group extraction pattern** — copy from lines 492-494:
```python
m_movie = RE_MOVIE.match(stem)
if m_movie:
    folder = f"{m_movie.group('title').strip()} ({m_movie.group('year')})"
```
For the proposal:
```python
title = re.sub(r"[_.]", " ", m.group("title")).strip()
year = m.group("year")
if not title:
    return None
canonical = f"{title} ({year}){path.suffix}"
new_path = path.parent / canonical
if new_path.name == path.name:   # no-op guard — do not emit spurious rows
    return None
return (str(path), str(new_path))
```

---

### `check_coherence(drive_root)` — scanner + console + file reporter

**Analog (scan):** `_organize_games()` scandir pattern — `organizer.py` lines 415-438
**Analog (summary print):** `_print_summary()` / `undo_last_run()` summary lines (lines 513-523, 662)

**scandir one-level pattern** — copy from `_organize_games()` lines 419-438:
```python
try:
    with os.scandir(src_dir) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                ...
            elif entry.is_file(follow_symlinks=False):
                p = Path(entry.path)
                if p.suffix.lower() in VIDEO_EXTS:
                    ...
except PermissionError:
    logger.warning("SKIP (permiso): %s", src_dir)
```

**COH-01 path prefix check** — Windows case-insensitive comparison required (pitfall 6):
```python
p_str = str(p).lower()
series_root_str = str(series_root).lower()
peliculas_root_str = str(peliculas_root).lower()
if not (p_str.startswith(series_root_str) or p_str.startswith(peliculas_root_str)):
    outside.append(p)
```

**Dual output pattern (console + file)** — no single direct analog; construct from `_print_summary()` (line 523) and `flush_undo_log()` (lines 528-540):
```python
# Console output — use print() not logger (user-visible)
for line in lines:
    print(line)

# File output — write_text is cleaner than open() for a single-write text report
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\n[OK] Reporte guardado en: {report_path}")
```
Note: coherence report uses UTF-8 without BOM (no Excel round-trip needed for a plain-text report).

**Output path convention** — same as all log outputs (lines 274, 528-534):
```python
report_path = drive_root / LOG_DIR_NAME / "coherence_report.txt"
report_path.parent.mkdir(parents=True, exist_ok=True)
```

**Summary line style** — copy ASCII `[OK]` convention from `_print_summary()` (line 523) and `undo_last_run()` (line 662):
```python
print(f"[OK] Reporte guardado en: {report_path}")
```

---

### `_normalize_for_dedup(stem)` — string normalizer utility

**Analog:** No direct analog in codebase. This is a pure string transform.

**Module-level regex convention** — copy compile pattern from SECTION 9 (lines 259-267):
```python
RE_NORM_STRIP = re.compile(
    r"\b(?:1080p|720p|480p|4[Kk]|2160p|x264|x265|h264|h265|avc|hevc"
    r"|bluray|blu-ray|bdrip|brrip|hdrip|webrip|web-dl|dvdrip|xvid"
    r"|hdr|sdr|dts|ac3|aac|mp3)\b",
    re.IGNORECASE,
)
```

**Normalization chain** — re.sub sequence; no analog but follows project style of chained substitutions:
```python
def _normalize_for_dedup(stem: str) -> str:
    s = re.sub(r"\((?:19|20)\d{2}\)", "", stem)  # strip (year)
    s = RE_NORM_STRIP.sub("", s)
    s = re.sub(r"[_.\-]+", " ", s)               # normalize separators
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s
```
Empty-key guard in caller: `if not key: continue` — prevents false COH-03 mega-group (pitfall 2).

---

### `show_menu()` edits — option 4 stub + option 6 addition

**Analog:** `show_menu()` itself — `organizer.py` lines 675-709

**Current state** (lines 685-705):
```python
print("  4) Detectar incoherencias")
print(f"  5) Dry-run: {dry_label}")
print("  0) Salir")
choice = input("Opcion: ").strip()
...
elif choice == "4":
    print("(Disponible en Fase 4)")
elif choice == "5":
    executor.dry_run = not executor.dry_run
```

**Target state** (copy surrounding choice blocks, lines 692-708, as structural model):
```python
print("  4) Detectar incoherencias")
print(f"  5) Dry-run: {dry_label}")
print("  6) Generar rename_plan.tsv")
print("  0) Salir")
...
elif choice == "4":
    check_coherence(Path(drive["root"]))
elif choice == "5":
    executor.dry_run = not executor.dry_run
elif choice == "6":
    generate_rename_plan(Path(drive["root"]))
```

Key: options 4 and 6 do NOT call `_prepare_executor_for_run()` or `_flush_and_clear()` — they are read-only operations. Compare with option 1 (lines 693-696) which does call both:
```python
# Option 1 — mutation path (DO NOT copy for options 4 or 6):
elif choice == "1":
    _prepare_executor_for_run(executor, drive)
    counts = organize_videos_and_games(executor, Path(drive["root"]))
    _print_summary(counts)
    _flush_and_clear(executor, log_path)
```

---

### New module-level regex constants (SECTION 16 header)

**Analog:** SECTION 9 — `organizer.py` lines 255-267

**Pattern to copy exactly:**
```python
# SECTION 9 — Compiled regex patterns (Phase 2)
# Ground truth: Ordenar.ps1 line 236 (series) and line 278 (movies).
# Compiled at module level — never inside a function or loop (CLAUDE.md convention).

RE_SERIES = re.compile(
    r"^(?P<show>.+?)\s-\sTemporada\s(?P<season>\d+)\s-\sEpisodio\s(?P<ep>\d+)",
    re.IGNORECASE,
)

RE_MOVIE = re.compile(
    r"^(?P<title>.+?)\s\((?P<year>(?:19|20)\d{2})\)",
    re.IGNORECASE,
)
```

New constants block at top of SECTION 16 follows identical structure:
```python
# SECTION 16 — Power features: compiled regex patterns (Phase 4)
# Compiled at module level — never inside a function or loop (CLAUDE.md convention).

RE_SERIES_VARIANT = re.compile(...)
RE_SERIES_SXXEXX  = re.compile(...)
RE_MOVIE_VARIANT  = re.compile(...)
RE_NORM_STRIP     = re.compile(...)
```

---

## Shared Patterns

### Safety guards (is_no_touch + should_skip_path)
**Source:** `organizer.py` lines 106-116 (SECTION 5)
**Apply to:** Any loop that iterates file paths in `generate_rename_plan()` and `check_coherence()`
```python
if is_no_touch(str(p)) or should_skip_path(str(p)):
    continue
```

### PermissionError handling on scandir
**Source:** `organizer.py` lines 437-438 (`_organize_games`) and line 373 (`_walk`)
**Apply to:** Every `os.scandir()` call in SECTION 16
```python
except PermissionError:
    logger.warning("SKIP (permiso denegado): %s", current_dir)
```

### [OK] ASCII summary style
**Source:** `organizer.py` line 523 (`_print_summary`) and line 662 (`undo_last_run`)
**Apply to:** Any final user-visible output line in SECTION 16 functions
```python
print(f"[OK] Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")
# Or for coherence:
print(f"\n[OK] Reporte guardado en: {report_path}")
```

### Path construction with LOG_DIR_NAME
**Source:** `organizer.py` line 37 and line 274
**Apply to:** All output file paths in SECTION 16
```python
LOG_DIR_NAME = "_organizer_logs"  # constant at line 37
out_path = drive_root / LOG_DIR_NAME / "rename_plan.tsv"
report_path = drive_root / LOG_DIR_NAME / "coherence_report.txt"
```

### logger vs print() split
**Source:** `organizer.py` throughout — pattern established in Phase 1-3
**Apply to:** All SECTION 16 functions
- `logger.warning(...)` / `logger.info(...)` — operational events (SKIP, MATCH, ERR)
- `print(...)` — user-facing summaries and interactive messages

### mkdir before write
**Source:** `organizer.py` lines 532-533 (`flush_undo_log`)
**Apply to:** Both file output calls in SECTION 16
```python
out_path.parent.mkdir(parents=True, exist_ok=True)
```

---

## No Analog Found

| Logical Unit | Role | Data Flow | Reason |
|---|---|---|---|
| `_normalize_for_dedup()` | utility/transform | transform | No string normalization utility exists yet in organizer.py; implement from first principles following CLAUDE.md re.compile convention |

---

## Integration Checklist for Planner

1. SECTION 16 must be inserted AFTER the final line of SECTION 15 (`undo_last_run` ends at line 672) and BEFORE SECTION 14's `show_menu` (line 675). The section numbering comment follows the SECTION N pattern established throughout organizer.py.
2. All four new regex constants (`RE_SERIES_VARIANT`, `RE_SERIES_SXXEXX`, `RE_MOVIE_VARIANT`, `RE_NORM_STRIP`) must appear at MODULE LEVEL — either grouped at the top of SECTION 16 before the function definitions, or appended after SECTION 9's block (lines 259-267). SECTION 16 grouping is preferred to keep Phase 4 code contiguous.
3. `show_menu()` edits are surgical: (a) add `print("  6) Generar rename_plan.tsv")` after the dry-run print, (b) replace `print("(Disponible en Fase 4)")` with `check_coherence(Path(drive["root"]))`, (c) add `elif choice == "6": generate_rename_plan(Path(drive["root"]))`.
4. COH-02 must NOT use `_scan_videos_recursive(drive_root, SCAN_EXCLUDE_DIR_NAMES)` for the series folder scan — `SCAN_EXCLUDE_DIR_NAMES` contains `"series"` which would exclude the folder we need to enter. Use direct `os.scandir(series_root)` instead (two levels: show dirs then episode files).

## Metadata

**Analog search scope:** `organizer.py` (entire file, lines 1-727); `Ordenar.ps1`; `Renombrar.ps1`
**Files scanned:** organizer.py (727 lines, read completely)
**Pattern extraction date:** 2026-04-21

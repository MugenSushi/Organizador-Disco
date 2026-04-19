# Feature Landscape

**Domain:** Local media file organizer CLI (video series/movies, game ROMs/ISOs, subtitles)
**Researched:** 2026-04-19
**Confidence:** HIGH (grounded in existing scripts + established tool ecosystem patterns)

---

## Table Stakes

Features users expect from any media organizer. Missing = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Detect & select removable drive at startup | Drive letter changes between sessions; hardcoded paths are the #1 friction point in both existing scripts | Low | Use `ctypes.windll` + `win32api` fallback via stdlib `subprocess`; show label + size |
| Organize series into `Series\Show\Temporada X\` | Core value; expected by anyone who's used FileBot or Plex | Low-Med | Must handle existing Ordenar.ps1 pattern exactly: `Show - Temporada X - Episodio Y` |
| Organize movies into `Peliculas\Title (Year)\` | Core value | Low | Año regex `(19|20)\d{2}` is the reliable signal |
| Organize games by system into `Juegos\<system>\` | Core value; replaces Ordenar.ps1 step 2 | Low | Systems: PC, PS1, PS2, PSP, GBA, GBC — folder-based, not extension-based for ROMs |
| Move subtitles co-located with their video | Users of VLC/MPC-HC expect `.srt`/`.ass`/`.sub`/`.idx` next to their video | Low | Match on basename only, same source directory |
| Hard skip for ROM/ISO extensions and system paths | Non-negotiable safety contract; violating this destroys trust permanently | Low | `.iso .bin .cue .img .mdf .nrg .chd .cso .pbp .gba .gbc .gb .nes .sfc .smc .n64 .z64 .v64 .3ds .cia .nds .gcm .wbfs .wad .xci .nsp` and `$RECYCLE.BIN`, `System Volume Information`, `Program Files`, `WindowsApps`, `Amazon Games` |
| Collision-safe destination paths | Without `(2)` / `(3)` suffixes, any conflict silently overwrites files | Low | Implemented in both PS1 scripts; must preserve |
| Dry-run mode (preview without moving) | Users always want to verify before committing, especially first run | Med | See dry-run section below |
| Undo / rollback last operation | One wrong run on a large drive is catastrophic without this | Med | See undo section below |
| Empty folder cleanup after moves | Leaves the drive clean; expected by power users | Low | Walk upward after each move, remove if empty; skip protected dirs |
| Persistent log per run | Users need to audit what happened; both PS1 scripts already do this | Low | `<drive>\_organizer_logs\` with timestamp in filename |
| Apply renames from `rename_plan.tsv` | Replaces Renombrar.ps1; the TSV is the user's reviewed rename contract | Low-Med | Must use `LiteralPath` equivalent (handle `[` `]` in filenames); skip ROMs/system |

---

## Differentiators

Features that make this tool meaningfully better than the PowerShell scripts it replaces. Not expected, but high value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| TSV rename plan generator | The user currently writes the TSV manually. Auto-generation with human review step is the #1 time saver | Med | See TSV section below |
| Coherence checker | Surfaces problems without fixing them — safe, audit-first | Med | See coherence section below |
| Interactive menu with numbered options | Zero learning curve; no need to remember flags or open script in editor | Low | Single-file, no argparse needed; loop back to menu after each action |
| Per-action dry-run report with counts | "X files would move, Y already in place, Z skipped (protected)" gives confidence before committing | Low-Med | Dry-run should print a table, not a raw log dump |
| Season gap detection | Tells user "you have S01, S03 but no S02" — useful when collecting | Low | Byproduct of coherence checker; trivial once episode inventory is built |
| Duplicate title detection | Same movie title in two different folders | Low | Normalize title (lowercase, strip year) for comparison |
| Orphaned subtitle detection | `.srt` without matching video — coherence check, not auto-fix | Low | List them; do not auto-delete |
| Misplaced video detection | Video file sitting at drive root or in wrong top-level folder | Low | Any `.mp4/.mkv` not under `Series\`, `Peliculas\`, or `Juegos\` |
| Readonly attribute clear before rename | Ordenar.ps1 already handles this; Python must too | Low | `os.chmod(path, stat.S_IWRITE)` |
| Run summary at end | "Moved 43 files, skipped 7, cleaned 12 empty folders, 0 errors" | Low | Print to both stdout and log |

---

## Anti-Features

Things to explicitly NOT build. Each has been consciously ruled out.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| CLI argument parsing (`argparse`) | PROJECT.md explicitly rules this out; adds complexity for occasional interactive use | Keep menu-driven; a single `--drive` shortcut is the maximum allowable |
| TMDB / TVDB / IMDb API lookups | Adds network dependency, API key management, rate-limit handling, and breakage risk; the user's naming convention is already well-defined | Trust the filename; the TSV review step is the correction mechanism |
| Auto-apply TSV renames without review step | User explicitly wants to review before applying — this is a safety requirement, not a preference | Generate TSV, open in default editor (or print path), then prompt "apply now?" |
| Music / photo organization | Out of scope per PROJECT.md; different domain with different rules | Document clearly that `.mp3/.flac/.jpg` are ignored |
| GUI / web interface | Not requested; terminal covers the use case entirely | A rich terminal with clear prompts is sufficient |
| Cloud sync / remote drives | Network paths introduce latency and partial-write risk on removable media | Validate that selected drive is local (`DriveType == DRIVE_REMOVABLE` or `DRIVE_FIXED`) |
| Automatic duplicate resolution (auto-delete) | Deleting files without explicit confirmation is unacceptable on a media drive | Flag duplicates in coherence report; require manual decision |
| Watch-folder / daemon mode | Adds persistent process, startup registration, complexity; not requested | One-shot runs are the correct model for occasional use |
| Recursive game folder reorganization | Ordenar.ps1 deliberately only moves top-level system folders to avoid breaking game installs | Keep the conservative "move folder contents, not deep recurse" approach |
| Subtitle language detection / renaming | Requires parsing sub file content or external API; high complexity, low value | Move subs by basename match only |

---

## Coherence Checker — What to Detect

The coherence checker is a read-only audit. It produces a report; it does not fix anything.

### Category 1: Misplaced Files (High Value)

- **Video at drive root** — any `*.mp4 *.mkv *.avi` directly under `X:\` (not in a subdirectory)
- **Video in wrong top-level folder** — e.g. a series episode sitting in `Peliculas\`, or a movie in `Series\`
  - Detection: file in `Series\` but name matches movie pattern `Title (Year)` (no episode markers)
  - Detection: file in `Peliculas\` but name matches series pattern `Show - Temporada X - Episodio Y`
- **Video in `Juegos\` subtree** — video extensions inside game directories are suspicious
- **Orphaned subtitle** — `.srt/.ass/.sub/.idx` with no matching video basename in same directory
- **Subtitle in wrong directory** — subtitle whose basename matches a video in a *different* directory

### Category 2: Series Structural Inconsistencies (High Value)

- **Episode not in season subfolder** — `Series\Show\Show - Temporada 1 - Episodio 3.mkv` (flat, should be in `Temporada 1\`)
- **Season gaps** — show has Temporada 1 and Temporada 3 but no Temporada 2 folder at all
- **Episode number gaps** — within a season, episodes jump (E01, E02, E05 — E03/E04 missing)
  - Report as warning only; gaps may be intentional (special episodes, skipped downloads)
- **Inconsistent naming within a show** — some episodes use `Temporada X - Episodio Y`, others use `SxxExx` or bare numbers
- **Mixed season folder formats** — `Temporada 1` and `Season 1` coexisting for same show

### Category 3: Duplicate Titles (Medium Value)

- **Duplicate movie folders** — `Peliculas\Inception (2010)\` and `Peliculas\Inception (2010) (2)\`
- **Same title different year** — `Peliculas\The Ring (2002)\` and `Peliculas\The Ring (2024)\` — flag, not error
- **Same movie in two formats** — same basename with `.mkv` and `.mp4` in same folder (keep highest quality, but do not auto-delete)
- **Normalization rule for comparison**: lowercase, remove articles (`the`, `el`, `la`, `los`, `las`), collapse whitespace, strip punctuation

### Category 4: Naming Format Violations (Lower Value)

- **Series file with no season/episode marker** — video in `Series\Show\Temporada X\` whose name does not match the expected pattern
- **Movie folder without year** — `Peliculas\Inception\` (no `(Year)`) makes Plex-style tools fail
- **Non-standard characters in filenames** — characters that cause issues on Windows or FAT32 (`: * ? " < > |`)

### Report Format

```
COHERENCE REPORT — X:\  [2026-04-19 14:32]
==============================================
MISPLACED FILES (3)
  [!] X:\Interstellar (2014).mkv — video at drive root
  [!] X:\Peliculas\Breaking Bad - Temporada 2 - Episodio 4.mkv — series file in Peliculas\
  [!] X:\Series\Loki\Temporada 1\Loki (2021).mkv — movie pattern inside Series\

SEASON GAPS (1)
  [?] Breaking Bad — Temporada 2 present, Temporada 1 missing

EPISODE GAPS (2)
  [?] Breaking Bad\Temporada 2 — episodes: 1,2,3,5,6 (gap at E04)
  [?] The Boys\Temporada 3 — episodes: 1,2,4,5,6,7,8 (gap at E03)

DUPLICATE TITLES (1)
  [=] Peliculas\Inception (2010)\ and Peliculas\Inception (2010) (2)\

ORPHANED SUBTITLES (2)
  [~] X:\Series\Stranger Things\Temporada 1\ep01_es.srt — no matching video

NAMING VIOLATIONS (1)
  [#] Peliculas\Inception\ — movie folder missing year

Total issues: 10  |  Critical: 3  |  Warnings: 7
```

---

## TSV Rename Plan Generator — Design

### What the Generator Scans For

The generator should detect files that are "close to but not quite" the canonical format. Patterns to detect:

**Series episode patterns to recognize and normalize to `Show - Temporada X - Episodio Y`:**

| Input Pattern | Example | Notes |
|---------------|---------|-------|
| `SxxExx` (standard international) | `Breaking.Bad.S02E05.mkv` | Most common for downloaded files |
| `S02E05` with spaces/dots/underscores | `Breaking Bad S02E05.mkv`, `Breaking_Bad_S02E05.mkv` | Separator normalization |
| `2x05` style | `Breaking.Bad.2x05.mkv` | Season × Episode |
| Bare `- XX -` with context | `Breaking Bad - 205 - Salud.mkv` | Ambiguous; flag for review |
| Already correct format | `Breaking Bad - Temporada 2 - Episodio 5.mkv` | No suggestion needed; skip |
| `Temporada X Episodio Y` (no dashes) | `Breaking Bad Temporada 2 Episodio 5.mkv` | Add dashes |
| `T02E05` | `Breaking.Bad.T02E05.mkv` | T = Temporada in Spanish rips |

**Movie patterns to recognize and normalize to `Title (Year)`:**

| Input Pattern | Example | Notes |
|---------------|---------|-------|
| `Title.Year.mkv` | `Inception.2010.mkv` | Dot-separated |
| `Title Year mkv` | `Inception 2010.mkv` | Space but no parens |
| `Title (Year) [extra tags]` | `Inception (2010) [1080p BluRay].mkv` | Strip tags after year |
| `Title.Year.Resolution.Source` | `Inception.2010.1080p.BluRay.mkv` | Strip all after year |
| Already correct | `Inception (2010).mkv` | Skip |

**Tags to strip (junk tokens):**
`1080p 720p 480p 4K UHD BluRay BDRip WEBRip WEB-DL HDTV x264 x265 HEVC AAC AC3 DTS HDR10 SDR PROPER REPACK EXTENDED THEATRICAL`

### TSV Format

```
old_path\told_name\tnew_name\treason
```

Four columns, tab-separated, UTF-8, BOM-less:
- `old_path` — absolute path to containing directory
- `old_name` — current filename (with extension)
- `new_name` — proposed filename (with extension)
- `reason` — human-readable explanation: `"S02E05 → Temporada 2 - Episodio 5"`, `"stripped [1080p BDRip]"`

The `reason` column is the key differentiator from Renombrar.ps1. It lets the user understand every suggestion at a glance.

### Human Review Step (Required)

1. Generate TSV, write to `<drive>\_organizer_logs\rename_plan.tsv`
2. Print path and row count to terminal
3. Prompt: `Open file now? [y/N]` — if yes, `os.startfile()` to open in default app (Notepad/Excel)
4. After user closes / returns: `Apply renames from current TSV? [y/N]`
5. Never auto-apply without explicit confirmation

### What NOT to Suggest

- Any file with a ROM/ISO extension
- Files already matching canonical format exactly
- Files with ambiguous patterns where confidence is low — mark as `# REVIEW` comment row instead
- Files in protected directories

---

## Dry-Run Report — What Good Looks Like

A dry-run is not a log file. It is a structured preview designed for human decision-making.

### Structure

```
DRY-RUN PREVIEW — X:\  [2026-04-19 14:32]
==========================================
[ORGANIZE SERIES]
  MOVE  X:\Breaking Bad - Temporada 2 - Episodio 5.mkv
     -> X:\Series\Breaking Bad\Temporada 2\Breaking Bad - Temporada 2 - Episodio 5.mkv
  MOVE  X:\Breaking Bad - Temporada 2 - Episodio 5.srt (subtitle)
     -> X:\Series\Breaking Bad\Temporada 2\Breaking Bad - Temporada 2 - Episodio 5.srt

[ORGANIZE MOVIES]
  MOVE  X:\Inception (2010).mkv
     -> X:\Peliculas\Inception (2010)\Inception (2010).mkv
  SKIP  X:\Inception (2010) [1080p].mkv  (reason: rename plan needed first)

[ORGANIZE GAMES]
  MOVE  X:\PS2\God of War\  (folder)
     -> X:\Juegos\PS2\God of War\

[CLEANUP EMPTY FOLDERS]
  RMDIR X:\PS2\  (will be empty after moves)

------------------------------------------
SUMMARY
  Would move:          43 files
  Would create dirs:   12
  Would remove dirs:    4 (empty)
  Already in place:     7 (skipped)
  Protected/skipped:    3
  Errors (preview):     0
------------------------------------------
To apply: select "Organizar" from main menu (dry-run is OFF)
```

### Key Design Rules

1. Show both source and destination for every MOVE — not just the filename
2. Group by operation type (series, movies, games, cleanup)
3. Summary numbers at the bottom with clear labels
4. Never paginate silently — if output is long, show count and offer to write to file
5. Distinguish "already in place" from "skip" — they mean different things
6. Dry-run output goes to stdout AND to `_organizer_logs\dryrun_<timestamp>.txt`
7. Errors during preview (e.g., permission check failures) are reported — they predict real errors

---

## Undo / Rollback — What to Store

### Log Schema (JSON)

```json
{
  "run_id": "2026-04-19T14-32-00",
  "drive": "X:\\",
  "operation": "organize",
  "timestamp_start": "2026-04-19T14:32:00",
  "timestamp_end": "2026-04-19T14:32:47",
  "moves": [
    {
      "type": "move",
      "src": "X:\\Breaking Bad - Temporada 2 - Episodio 5.mkv",
      "dst": "X:\\Series\\Breaking Bad\\Temporada 2\\Breaking Bad - Temporada 2 - Episodio 5.mkv",
      "dirs_created": ["X:\\Series\\Breaking Bad\\", "X:\\Series\\Breaking Bad\\Temporada 2\\"]
    }
  ],
  "dirs_removed": [
    "X:\\PS2\\"
  ],
  "renames": [
    {
      "type": "rename",
      "path": "X:\\Series\\Breaking Bad\\Temporada 2\\",
      "old_name": "Breaking.Bad.S02E05.mkv",
      "new_name": "Breaking Bad - Temporada 2 - Episodio 5.mkv"
    }
  ]
}
```

### Undo Logic Rules

1. **Process in reverse order** — undo the last move first; this prevents conflicts when a file was moved twice
2. **Recreate source directory if removed** — if the directory was empty and deleted, recreate it before moving file back
3. **Undo dirs_created in reverse** — only remove a created directory if it is currently empty (do not remove if user added files after)
4. **Collision handling on undo** — if `src` path now exists (user put something there), do not overwrite; report conflict and skip
5. **Never undo past one run** — only the most recent run's log is offered for undo; stacking undo is complex and error-prone
6. **Log the undo itself** — write a separate `undo_<run_id>.log` so there is always an audit trail
7. **Renames and moves are separate** — a rename-then-organize run stores rename entries and move entries; undo moves first, then un-renames
8. **Undo is opt-in, not automatic** — always show what will be reversed and ask for confirmation before executing

### Log File Location

`<drive>\_organizer_logs\run_<YYYY-MM-DD_HHMMSS>.json`

Keep the last 10 run logs; on startup, prune older ones silently.

---

## Feature Dependencies

```
Drive detection
  └─> All operations (nothing works without a selected drive)

TSV generator
  └─> Apply TSV renames (must generate before applying)

Organize (series/movies/games)
  └─> Undo (must log moves to enable rollback)
  └─> Empty folder cleanup (runs after organize)

Coherence checker
  └─> Organize (checker is more useful after organize; run post-organize or standalone)

Dry-run
  └─> Organize (dry-run is the preview mode of organize; shares same detection logic)
```

---

## MVP Recommendation

Prioritize in this order:

1. **Drive detection + menu shell** — everything else depends on this; build it first
2. **Organize (series + movies + games + subs)** with undo log — core value; must be solid
3. **Dry-run** — safety net; build alongside Organize, not after
4. **Apply TSV renames** — replaces Renombrar.ps1 directly; low complexity
5. **Empty folder cleanup** — natural finish step of Organize
6. **TSV generator** — significant time saver; medium complexity
7. **Coherence checker** — high value but read-only; does not block any other feature

Defer to later phases:
- Episode gap detection (extend coherence checker once series inventory logic exists)
- Season gap detection (same)
- Duplicate title detection (same)

---

## Sources

- Ordenar.ps1 and Renombrar.ps1 (existing scripts, direct feature extraction)
- PROJECT.md (explicit scope and constraints)
- FileBot / tinyMediaManager / Plex Scanner established conventions (domain expertise, HIGH confidence)
- Rsync/robocopy dry-run patterns (established CLI convention for preview mode, HIGH confidence)
- Git-style undo log schema (established pattern for reversible operations, HIGH confidence)

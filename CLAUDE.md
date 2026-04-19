<!-- GSD:project-start source:PROJECT.md -->
## Project

**Organizador de Disco**

Script Python de terminal para organizar discos extraíbles con medios (vídeos, juegos, ROMs).
Al arrancar detecta las unidades extraíbles disponibles y pregunta cuál usar; luego ofrece un menú
con todas las operaciones disponibles. Unifica y mejora dos scripts PowerShell preexistentes.

**Core Value:** Organizar una unidad seleccionada en segundos sin miedo a errores, gracias al dry-run y el undo.

### Constraints

- **Tech stack**: Python 3.x puro — sin dependencias externas (solo stdlib)
- **Compatibilidad**: Windows únicamente (os, shutil, pathlib, ctypes para detectar discos extraíbles)
- **Seguridad**: nunca tocar extensiones ROM/ISO ni rutas del sistema — hard block
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### File System Operations
| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `pathlib.Path` | 3.4+ | All path construction, stat, glob, iterdir | Object-oriented API, `/` operator for joining, `.stem`/`.suffix`/`.name` attributes, reads clean |
| `shutil` | stdlib | Move and copy files with metadata | `shutil.move()` handles cross-filesystem moves atomically when possible; `shutil.copy2()` preserves timestamps |
| `os` | stdlib | `os.replace()` for atomic overwrite, `os.makedirs(exist_ok=True)` | Needed for the few operations pathlib delegates to os under the hood |
### Drive Detection
| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `ctypes` | stdlib | Call `GetLogicalDrives` + `GetDriveTypeW` from `kernel32` | Zero subprocess overhead, no external tool dependency, pure API call |
| `subprocess` | stdlib | Fallback: `wmic logicaldisk` or PowerShell `Get-Volume` | Use only if ctypes fails (e.g., unusual Python build); adds latency |
### Data Persistence
| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `json` | stdlib | Undo log — record every move as a JSON array of `{src, dst, timestamp}` | Human-readable, trivially reversible by reading and swapping src/dst, `json.dump(indent=2, ensure_ascii=False)` for legibility |
| `csv` | stdlib | Read `rename_plan.tsv` with `delimiter='\t'` | Official TSV reading pattern; `dialect='excel-tab'` or explicit `delimiter='\t'`; always `newline=''` and `encoding='utf-8-sig'` to handle BOM from Excel |
### Pattern Matching
| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `re` | stdlib | Match series/movie/ROM filenames | `re.compile()` at module level for patterns used in loops; group names over numbered groups for readability |
### Logging
| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `logging` | stdlib | Operational log to `<drive>\_organizer_logs\` | Thread-safe, level-filtered, `RotatingFileHandler` prevents unbounded growth; dual output: file + console |
### Menu / CLI
| Module | Purpose | Why |
|--------|---------|-----|
| `input()` + plain `print()` | Interactive menu loop | No curses (Windows console support is broken/partial), no readline dependency; a numbered menu with a `while True` loop is the correct pattern |
## Module-by-Module Patterns
### pathlib — File Operations
# Move via shutil (not Path.rename — crosses directories reliably)
### ctypes — Removable Drive Detection (PRIMARY)
- `0` = DRIVE_UNKNOWN
- `1` = DRIVE_NO_ROOT_DIR
- `2` = DRIVE_REMOVABLE  ← what we want
- `3` = DRIVE_FIXED
- `4` = DRIVE_REMOTE
- `5` = DRIVE_CDROM
- `6` = DRIVE_RAMDISK
### subprocess — Drive Detection (FALLBACK ONLY)
### json — Undo Log
# Log path convention
### csv — TSV Reading
### re — Media Filename Patterns
# Compile once at module level — not inside functions
# ROM/ISO extensions — no regex needed, just a frozen set
### logging — Dual Output (File + Console)
### Menu Loop — input() Pattern
## Alternatives Considered and Rejected
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Path API | `pathlib` | `os.path` | `os.path` is procedural string manipulation; pathlib is idiomatic Python 3.4+, cleaner, fewer mistakes |
| Drive detection | `ctypes.windll` | `subprocess + wmic` | subprocess spawns a child process, adds 200–500ms startup time, WMIC is deprecated on Win11 |
| Drive detection | `ctypes.windll` | `subprocess + PowerShell` | PowerShell startup is even slower (~1s), and adds a dependency on PowerShell being in PATH |
| Undo log | `json` (full array) | JSONL (one entry per line) | JSONL is harder to reverse cleanly; full array is one `json.load()` call for undo |
| Undo log | `json` | `sqlite3` | Overkill for a single-session undo log; JSON is human-inspectable |
| Menu | `input()` | `curses` | curses on Windows requires `windows-curses` (not stdlib); breaks the zero-dependency constraint |
| Menu | `input()` | `argparse` | argparse is for CLI argument parsing, not interactive menus; project explicitly excluded CLI args |
| Logging | named logger + handlers | `logging.basicConfig()` | basicConfig is fragile (no-op if handlers exist), harder to configure dual output |
| Logging | `logging` module | manual `open().write()` | logging module handles rotation, levels, thread safety automatically |
| File move | `shutil.move()` | `Path.rename()` | `Path.rename()` fails across filesystems/drives and has undefined behavior when destination exists |
| TSV reading | `csv.DictReader(delimiter='\t')` | manual `line.split('\t')` | manual split breaks on quoted fields, doesn't handle edge cases |
## Installation
# These are all the imports the project needs — zero pip installs
## Confidence Levels Per Recommendation
| Recommendation | Confidence | Source |
|----------------|------------|--------|
| pathlib over os.path | HIGH | Official Python docs, Python 3.4+ design intent |
| shutil.move for moves | HIGH | Official shutil docs — explicit cross-filesystem behavior documented |
| ctypes.windll for drive detection | HIGH | Official ctypes docs + GetDriveTypeW Windows API constants |
| subprocess as fallback only | HIGH | Official subprocess docs — subprocess.run patterns verified |
| json for undo log | HIGH | Official json docs — dump/load patterns verified |
| csv with dialect='excel-tab' | HIGH | Official csv docs — excel-tab dialect is registered stdlib |
| utf-8-sig encoding for TSV | MEDIUM | Standard practice for Excel-generated files; not explicitly in csv docs |
| re.compile at module level | HIGH | Official re docs — explicit recommendation for repeated use |
| named groups in regex | HIGH | Official re docs |
| input() menu over curses | HIGH | curses Windows limitation is documented; windows-curses not in stdlib |
| Named logger over basicConfig | MEDIUM | Official logging docs state basicConfig is no-op if handlers exist; recommendation inferred from docs, not explicit |
| RotatingFileHandler 2MB/3 | MEDIUM | Standard practice; specific values are project judgment calls |
## Sources
- https://docs.python.org/3/library/pathlib.html
- https://docs.python.org/3/library/shutil.html
- https://docs.python.org/3/library/ctypes.html
- https://docs.python.org/3/library/subprocess.html
- https://docs.python.org/3/library/json.html
- https://docs.python.org/3/library/csv.html
- https://docs.python.org/3/library/re.html
- https://docs.python.org/3/library/logging.html
- https://docs.python.org/3/library/logging.handlers.html
- https://docs.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getdrivetypew (GetDriveTypeW constants)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

# Phase 1: Infrastructure - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the script skeleton: removable-drive detection, drive selection UI, safety guards (ROM/ISO block + system-path block), the Executor class with dry_run flag, collision-safe path helper, and the numbered main menu shell. At the end of this phase the script can boot, select a drive, and safely *describe* any future file operation without touching the filesystem.

New file operations, undo UI, and analytical features are NOT in scope — they land in Phases 2-4.

</domain>

<decisions>
## Implementation Decisions

### Drive Selection UX

- **D-01:** If exactly **one** removable drive is detected, auto-select it silently — print `Usando F:\ (NOMBRE)` and go straight to the menu. No confirmation prompt needed.
- **D-02:** If **no** removable drives are detected, print a clear error message (e.g., `No se encontraron unidades extraíbles. Conecta un disco e inténtalo de nuevo.`) and exit. No retry loop, no manual-path fallback.
- **D-03:** If **multiple** removable drives are detected, list them as numbered options showing letter + label + size — e.g., `1) F:\ MEDIOS (931 GB)`. User types the number to select.

### Claude's Discretion

- Menu shell completeness — user skipped this gray area. Claude may decide how many placeholder entries (if any) to show for Phase 2-4 features in the Phase 1 menu shell.
- Safety block verbosity — user skipped this gray area. Claude may decide whether ROM/ISO skips are silent-count-only or print per-item warnings.
- Internal code structure (constants → helpers → classes → main loop) within the single `.py` file.
- Logging configuration: level, format, RotatingFileHandler size — follow CLAUDE.md tech stack guidance (2 MB / 3 backups, dual file+console output). Console-only until drive is selected (no log path yet).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/REQUIREMENTS.md` — All v1 requirements; Phase 1 covers INFRA-01..INFRA-08, MENU-01
- `.planning/PROJECT.md` — Core value, constraints, key decisions table
- `CLAUDE.md` — Full tech stack table with recommended modules, patterns, and rejected alternatives

### Reference implementations (PowerShell)
- `Ordenar.ps1` — Existing organizer: drive detection via WMI, ROM/ISO block list, system-path skip list, series/movie/game patterns
- `Renombrar.ps1` — Existing renamer: TSV rename logic, LiteralPath usage

No external specs or ADRs — requirements are fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Ordenar.ps1` — reference for `$NO_TOUCH_EXTS` list (translate to Python frozenset), `$SKIP_PATH_PARTS` list, and preferred-drive fallback logic
- `Renombrar.ps1` — reference for TSV rename pattern (Phase 2, not Phase 1)

### Established Patterns
- Drive detection in `Ordenar.ps1` uses WMI (`Get-WmiObject Win32_LogicalDisk`). Python equivalent is `ctypes.windll.kernel32.GetDriveTypeW` (DRIVE_REMOVABLE = 2) — already decided as the primary approach.
- ROM/ISO extension list in `Ordenar.ps1` is the ground truth for the Python `NO_TOUCH_EXTS` frozenset.
- System-path skip list in `Ordenar.ps1` is the ground truth for `SKIP_PATH_PARTS`.

### Integration Points
- All file-moving logic in Phases 2-4 must go through `Executor.move()` — the dry_run flag lives there.
- Log path convention: `<drive>\_organizer_logs\` — must be created if absent when first needed.

</code_context>

<specifics>
## Specific Ideas

- Drive listing format confirmed: `1) F:\ MEDIOS (931 GB)` — letter, volume label, and total size.
- Single-drive auto-select message format: `Usando F:\ (NOMBRE)` — brief, informational.
- No manual path entry fallback — keeps the surface area minimal and safe.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-infrastructure*
*Context gathered: 2026-04-19*

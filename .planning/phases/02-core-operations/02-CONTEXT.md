# Phase 2: Core Operations - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 wires in all file-moving operations: renames from TSV, organize series/movies/game consoles into folder structure, subtitle co-location, and empty-folder cleanup. At the end of this phase the user can fully organize a drive from the menu.

Undo UI, run summaries wired to menu, TSV generation, and coherence checking are NOT in scope — those land in Phases 3-4.

</domain>

<decisions>
## Implementation Decisions

### Dry-run activation (MENU-02)

- **D-01:** Dry-run se activa/desactiva con la **opción 5 del menú principal**: `5) Dry-run: OFF` → al pulsarla cambia a `5) Dry-run: ON`. Toggle numerado visible en el menú en todo momento.
- **D-02:** Con dry-run activo, al elegir una operación (1 o 2) esta **se ejecuta en seco directamente**, sin confirmación ni aviso extra — el usuario ya sabe el estado porque lo ve en el menú.
- **D-03:** El estado dry-run **persiste hasta que el usuario lo desactiva manualmente**. No se reinicia entre operaciones. Permite revisar varias operaciones consecutivas antes de ejecutar en real.

### Exclusiones en organización de Juegos (ORG-03)

- **D-04:** La carpeta `PC\` (y `Steam\` si existe en la raíz de la unidad) se **excluyen completamente** de ORG-03. Solo se organizan las carpetas de consola: `PS1`, `PS2`, `PSP`, `GBA`, `GBC`. Motivo: juegos de PC instalados tienen dependencias de registro y rutas absolutas que se rompen al mover.
- **D-05:** Las exclusiones de `SKIP_PATH_PARTS` ya definidas en Phase 1 son suficientes para el resto. No se añaden exclusiones adicionales.

### Claude's Discretion

- **Ámbito del escaneo al organizar** — Claude decide qué carpetas raíz excluir del escaneo de Series/Películas (recomendado: excluir `_organizer_logs\`, `Juegos\`, `Series\`, `Peliculas\` para evitar doble-organización).
- **Formato de rutas en rename_plan.tsv** — Claude decide si las rutas son absolutas o relativas a la unidad. Recomendado: absolutas, consistente con el comportamiento del PS1 existente (`Ordenar.ps1`, `Renombrar.ps1`).
- **Formato del resumen final (MENU-03)** — Claude decide el formato. Recomendado: una línea compacta antes de volver al menú: `✓ Procesados: 47 | Movidos: 32 | Saltados: 12 | Errores: 3`.
- **Estructura interna de módulos** — Claude organiza las funciones de Phase 2 dentro de `organizer.py` según los patrones establecidos en Phase 1.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: RENAME-01, RENAME-02, ORG-01, ORG-02, ORG-03, ORG-04, ORG-05, MENU-02, MENU-03
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `CLAUDE.md` — Tech stack table, patterns, rejected alternatives

### Phase 1 artifacts (foundation)
- `.planning/phases/01-infrastructure/01-CONTEXT.md` — Decisions D-01..D-03 (drive selection) y patrones establecidos
- `.planning/phases/01-infrastructure/01-01-SUMMARY.md` — Interfaces exactas: Executor, drive dict, logger, show_menu signatures
- `organizer.py` — Código Phase 1 ya implementado — leer antes de cualquier adición

### Reference implementations (PowerShell ground truth)
- `Ordenar.ps1` — Implementación de referencia: patrones de series (`" - Temporada X - Episodio Y"`), películas (`"Título (Año)"`), juegos (sistemas de consola), exclusiones de carpetas, co-localización de subtítulos
- `Renombrar.ps1` — Implementación de referencia: lectura de TSV con `-LiteralPath`, manejo de comodines en nombres de archivo

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Executor.move(src, dst)` — ya implementado con dry_run, hard blocks, _free_path. Phase 2 llama esto para TODOS los movimientos.
- `Executor.ensure_dir(path)` — ya implementado, respeta dry_run.
- `Executor.dry_run` — atributo mutable; `show_menu()` debe hacer `executor.dry_run = True/False` al toggle.
- `show_menu(executor, drive)` — ya implementado con stubs 1-4 y loop. Phase 2 rellena los stubs 1 y 2 y añade la opción 5 (toggle dry-run).
- `logger` — módulo-level, ya configurado con RotatingFileHandler tras seleccionar unidad.

### Established Patterns
- `os.scandir` con context manager para traversal — nunca `glob`/`rglob` (INFRA-05, corchetes en nombres)
- `shutil.move(str(src), str(dst))` — nunca `Path.rename()` (falla cross-filesystem)
- `csv.DictReader(f, delimiter='\t')` con `newline=''` y `encoding='utf-8-sig'` para TSV (maneja BOM de Excel)
- Regex compilado a nivel de módulo para patrones usados en bucles
- Hard blocks siempre en `Executor.move()` — nunca en los call sites

### Integration Points
- `show_menu()` en `organizer.py`: Phase 2 debe reemplazar los stubs de opciones 1 y 2, y añadir opción 5.
- `Executor` instance creada en `main()` y pasada a `show_menu()` — Phase 2 la usa directamente.
- `drive['root']` — raíz de la unidad seleccionada, punto de partida para todos los paths.

</code_context>

<specifics>
## Specific Ideas

- **Dry-run toggle en menú**: `5) Dry-run: OFF` cambia a `5) Dry-run: ON` — texto cambia con el estado.
- **Exclusión de PC**: la carpeta `PC\` y `Steam\` en raíz de unidad se saltan en ORG-03 sin error ni warning — simplemente no se procesan.
- **Solo consolas en ORG-03**: PS1, PS2, PSP, GBA, GBC — estos son ROMs/archivos que no tienen dependencias de sistema.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-core-operations*
*Context gathered: 2026-04-19*

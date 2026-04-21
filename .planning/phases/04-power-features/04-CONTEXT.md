# Phase 4: Power Features - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 adds two new capabilities: (1) a TSV rename plan generator that scans the drive and proposes normalizations for series, movies, and misplaced game files; (2) a coherence checker that audits the drive structure and reports problems without moving anything.

At the end of this phase the user can discover rename candidates automatically and detect structural problems without manual inspection.

What is NOT in scope: auto-applying any renames (always user-reviewed), SxxExx pattern normalization (V2-01), external API lookups, bulk-delete.

</domain>

<decisions>
## Implementation Decisions

### Generador de rename_plan.tsv (RENAME-03, RENAME-04)

- **D-01:** El generador detecta tres categorías de archivos:
  1. **Series** — archivos de vídeo con estructura reconocible (show, temporada, episodio) pero en formato distinto al esperado (p.ej. S01E05, separadores raros). RE_SERIES ya existe para el formato correcto; el generador necesita detectar variantes y proponer la forma canónica.
  2. **Películas** — archivos de vídeo con título + año reconocibles pero formato incorrecto. RE_MOVIE ya existe para la forma canónica.
  3. **Juegos fuera de lugar** — archivos de consola (por extensión o nombre de carpeta de sistema de juego) que están fuera de `Juegos\<sistema>\` y propone moverlos al lugar correcto.

- **D-02:** El generador **solo normaliza lo que ya reconoce**. Si un archivo no tiene la estructura suficiente para inferir el nombre correcto (show, temporada, episodio / título + año), lo omite completamente. Cero placeholders, cero falsos positivos.

- **D-03:** El TSV generado se guarda en `_organizer_logs\rename_plan.tsv` (mismo path que usa `apply_renames()`). Nunca se auto-aplica — el usuario lo revisa y luego usa opción 2 del menú para aplicarlo (PROJECT.md Key Decision ya establecida).

- **D-04:** El generador se expone como una nueva opción del menú. La opción 4 ya está reservada para "Detectar incoherencias" → el generador va en **opción 6**: `6) Generar rename_plan.tsv`. El menú queda: 1) Organizar, 2) Aplicar rename, 3) Revertir, 4) Detectar incoherencias, 5) Dry-run toggle, 6) Generar rename_plan.tsv, 0) Salir.

### Coherence checker (COH-01, COH-02, COH-03)

- **D-05:** El reporte de coherencia es output-only — nunca mueve archivos. Detecta los tres problemas definidos en los requisitos: (a) vídeos fuera de Series\/Peliculas\, (b) episodios de series sin carpeta de temporada, (c) títulos duplicados por nombre normalizado.

### Claude's Discretion

- **Formato de salida del reporte de coherencia** — Imprime a consola Y escribe a `_organizer_logs\coherence_report.txt` (más útil que solo consola para unidades grandes). Claude decide el formato exacto de las líneas.
- **Normalización para duplicados (COH-03)** — Claude decide el algoritmo de normalización: strip año (entre paréntesis), strip tags de resolución (1080p, 720p, 4K, x264, x265, BluRay, HDRip, WEBRip, etc.), lowercase, strip espacios extra. Comparación exact-match sobre el resultado normalizado.
- **Patrones adicionales para el generador (D-01 variantes)** — Claude decide qué variantes de separador o formato de episodio detectar para series y películas (p.ej. guiones bajos, puntos como separadores).
- **Estructura interna de SECTION 16** — Claude organiza las funciones de Phase 4 en `organizer.py` siguiendo el patrón de secciones ya establecido.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/REQUIREMENTS.md` — Phase 4 requirements: RENAME-03, RENAME-04, COH-01, COH-02, COH-03
- `.planning/PROJECT.md` — Core value, constraints, key decisions (especialmente: TSV nunca auto-aplicado)
- `CLAUDE.md` — Tech stack, patterns, rejected alternatives

### Prior phase artifacts (foundation)
- `.planning/phases/02-core-operations/02-CONTEXT.md` — D-04 (exclusión PC/Steam en juegos), D-01..D-03 (dry-run), Claude's Discretion sobre rutas TSV
- `.planning/phases/02-core-operations/02-01-SUMMARY.md` — Interfaces de apply_renames(), _scan_videos_recursive(), RE_SERIES, RE_MOVIE
- `.planning/phases/03-safety-features/03-CONTEXT.md` — D-01..D-04 (undo log), show_menu signature con drives param
- `organizer.py` — Código actual completo — leer antes de cualquier adición (especialmente SECTION 9, 10, 11, 14)

### Reference implementations
- `Ordenar.ps1` — Ground truth para patrones de series/películas y exclusiones de carpetas
- `Renombrar.ps1` — Ground truth para manejo de TSV con -LiteralPath

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RE_SERIES` (organizer.py:259) — regex para el formato canónico de series; reutilizable para detectar si un archivo ya está bien nombrado
- `RE_MOVIE` (organizer.py:264) — regex para el formato canónico de películas
- `_scan_videos_recursive(root, exclude_roots)` (organizer.py:343) — scanner os.scandir recursivo ya implementado; aceptar el mismo `exclude_roots` frozenset
- `apply_renames()` (organizer.py:272) — ya conoce el formato TSV (old_path/new_path, tab, utf-8-sig); el generador debe producir exactamente ese formato
- `is_no_touch()` + `should_skip_path()` (organizer.py:106-117) — guards de ROM/sistema; aplicar antes de cualquier escaneo
- `LOG_DIR_NAME` (organizer.py:36) — constante `"_organizer_logs"` para construir paths de output
- `_print_summary()` (organizer.py:513) — patrón de resumen `[OK] Procesados: N | ...` para imprimir resultado

### Established Patterns
- `os.scandir` exclusivamente para escanear (INFRA-05 — maneja brackets en nombres)
- Regex compilados a nivel de módulo, nunca dentro de funciones (CLAUDE.md)
- Funciones de Phase N añadidas en SECTION N de organizer.py
- Menú con stubs `print("(Disponible en Fase N)")` — opción 4 es el coherence checker

### Integration Points
- `show_menu()` (organizer.py:675) — añadir opción 6 para el generador y reemplazar el stub de opción 4 con la llamada al coherence checker
- `_organizer_logs\rename_plan.tsv` — output del generador, input de `apply_renames()`
- `_organizer_logs\coherence_report.txt` — output del coherence checker (nuevo archivo)

</code_context>

<specifics>
## Specific Ideas

- El generador de juegos detecta archivos **fuera** de `Juegos\<sistema>\` — no revisa los que ya están dentro. Complementa la organización automática (opción 1) para casos que la organización no pudo mover automáticamente.
- El SxxExx format (S01E05) está en V2-01 (mejoras futuras) — NO está en scope de Phase 4. Si el generador encuentra SxxExx, puede intentar convertirlo a "Show - Temporada X - Episodio Y" si el show name es inferible, o ignorarlo.

</specifics>

<deferred>
## Deferred Ideas

- **SxxExx como patrón primario** (V2-01) — sería ampliar el soporte de patrones más allá de normalizar a formato canónico. Pertenece a v2.
- Ningún otro desvío de scope durante la discusión.

</deferred>

---

*Phase: 04-power-features*
*Context gathered: 2026-04-21*

# Phase 6: v2 — Consolidated "Ordenar Todo" - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Source:** User request via CLI

<domain>

## Phase Boundary

Consolidar el menú de opciones en una sola opción "Ordenar todo" que ejecuta todas las operaciones de organización en una pasada.

</domain>

<decisions>

## Implementation Decisions

### Menu Structure
- Opción única "Ordenar todo" que ejecuta en secuencia:
  1. `organize_videos_and_games()` — vídeos (Series/Películas), juegos consola, subtítulos
  2. `organize_other_files()` — documentos (DOCS), juegos PC (Juegos PC), software (Software)
  3. `_remove_empty_dirs()` — limpieza de carpetas vacías
- Eliminar opción separada "Organizar documentos, juegos PC y software"
- Mantener: apply renames, undo, coherence, dry-run toggle, generate rename plan, exit
- Numeración: 1=Ordenar todo, 2=Aplicar renames, 3=Undo, 4=Coherence, 5=Dry-run, 6=Generar rename plan, 0=Exit

### Función a crear
- Nueva función `organize_all(executor, drive_root)` que encadena las 3 operaciones
- El summary final combina los contadores de las 3 operaciones

### Seguridad
- Todos los safety checks (dry-run, undo, hard blocks) funcionan igual que antes
- Undo log registra correctamente los movimientos de todas las operaciones

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `organizer.py` — Código actual (show_menu, organize_videos_and_games, organize_other_files, _remove_empty_dirs)
- `.planning/REQUIREMENTS.md` — Requisitos v2 (V2-05, V2-06)
- `.planning/phases/03-01-PLAN.md` — Cómo se conectan executor y undo en el menú

</canonical_refs>

<specifics>

## Specific Ideas

Menú actual (7 opciones + exit):
1. Organizar videos y juegos
2. Organizar documentos, juegos PC y software
3. Aplicar rename_plan.tsv
4. Revertir ultima operacion
5. Detectar incoherencias
6. Dry-run toggle
7. Generar rename_plan.tsv
0. Salir

Menú nuevo (6 opciones + exit):
1. Ordenar todo
2. Aplicar rename_plan.tsv
3. Revertir ultima operacion
4. Detectar incoherencias
5. Dry-run toggle
6. Generar rename_plan.tsv
0. Salir

</specifics>

<deferred>

## Deferred Ideas

None — this phase covers the full consolidation scope.

</deferred>

---

*Phase: 06-v2-consolidated*
*Context gathered: 2026-04-22 via user request*
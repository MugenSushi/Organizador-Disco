# Organizador de Disco

## What This Is

Script Python de terminal para organizar discos (internos y extraíbles) con medios (vídeos, juegos, ROMs).
Al arrancar detecta todas las unidades disponibles y pregunta cuál usar; luego ofrece un menú
con todas las operaciones disponibles. Unifica y mejora dos scripts PowerShell preexistentes.

## Core Value

Organizar una unidad seleccionada en segundos sin miedo a errores, gracias al dry-run y el undo.

## Requirements

### Validated

- [x] Undo: guardar log JSON de movimientos y permitir revertir la última ejecución — Validated in Phase 3: Safety Features

### Active

- [x] Detectar todos los discos (internos y extraíbles) al inicio y preguntar cuál usar — Implemented: detección via GetDriveTypeW de discos FIXED y REMOVABLE
- [ ] Menú principal de terminal (sin argumentos CLI)
- [ ] Aplicar renombrados desde rename_plan.tsv existente (robusto: LiteralPath, skip ROMs/rutas sistema)
- [ ] Generar rename_plan.tsv automáticamente (solo sugerir, abre archivo para revisar antes de aplicar)
- [ ] Organizar Juegos: mover PC/PS1/PS2/PSP/GBA/GBC a Juegos\<sistema>\
- [ ] Organizar Series: detectar patrón "Show - Temporada X - Episodio Y", mover a Series\Show\Temporada X\
- [ ] Organizar Películas: detectar "Título (Año)", mover a Peliculas\Título (Año)\
- [ ] Mover subtítulos (.srt/.ass/.sub/.idx) junto al vídeo correspondiente
- [ ] Dry-run / Preview: simular todas las operaciones sin mover nada
- [ ] Limpieza de carpetas vacías tras mover archivos
- [ ] Detector de incoherencias: reportar vídeos fuera de lugar, series sin carpeta de temporada, duplicados de nombre

### Out of Scope

- Argumentos CLI — el usuario prefiere menú interactivo; CLI añadiría complejidad sin beneficio claro
- Organización de música/fotos — fuera del dominio del proyecto (medios de entretenimiento únicamente)
- GUI gráfica — no pedida; la terminal cubre el caso de uso
- Conexión a APIs externas (TMDB, TVDB) — añade dependencias y complejidad; los nombres ya siguen formato propio

## Context

- Dos scripts PowerShell preexistentes: Renombrar.ps1 (básico) y Ordenar.ps1 (completo con protecciones)
- El disco preferido era F:\ en Ordenar.ps1 y E:\ en Renombrar.ps1 — ahora se selecciona al inicio
- Los archivos ROM/ISO y carpetas de sistema (Program Files, $RECYCLE.BIN, etc.) nunca deben tocarse
- El formato de series ya establecido: "NombreSerie - Temporada X - Episodio Y"
- Los logs van en <disco>\_organizer_logs\

## Constraints

- **Tech stack**: Python 3.x puro — sin dependencias externas (solo stdlib)
- **Compatibilidad**: Windows únicamente (os, shutil, pathlib, ctypes para detectar discos)
- **Seguridad**: nunca tocar extensiones ROM/ISO ni rutas del sistema — hard block

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python en lugar de PowerShell | Más portable, más legible, más fácil de extender | — Pending |
| Solo sugerir TSV (no auto-aplicar) | El usuario quiere revisar antes de renombrar | — Pending |
| Menú interactivo sin CLI args | Más simple para el caso de uso (uso ocasional, no scripting) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 — Phase 3 complete: undo/rollback implemented; drive detection expanded to include internal drives*





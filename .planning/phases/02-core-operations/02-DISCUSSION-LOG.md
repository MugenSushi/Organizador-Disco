# Phase 2: Core Operations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 02-core-operations
**Areas discussed:** Dry-run activation, Exclusiones en organización de Juegos

---

## Dry-run activation

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle numerado | Opción 5 en menú principal, estado visible. `5) Dry-run: OFF/ON` | ✓ |
| Prompt antes de ejecutar | Pregunta `¿Modo simulación? [s/N]` antes de cada operación | |
| Cabecera del menú | Estado en título `=== Organizador [DRY-RUN] \| F:\\ MEDIOS ===` | |

**User's choice:** Toggle numerado (Recomendado)
**Notes:** Sin confirmación extra al ejecutar con dry-run activo. Estado persiste hasta desactivar manualmente.

---

## Exclusiones en organización de Juegos

| Option | Description | Selected |
|--------|-------------|----------|
| Excluir PC completamente | Solo consolas PS1/PS2/PSP/GBA/GBC — PC ignorada | ✓ |
| Mover PC solo ROMs/archivos sueltos | Solo archivos sueltos en PC\, no subcarpetas | |
| Mover PC igual que consolas | Mover contenido de PC\ a Juegos\PC\ igual que PS1 | |

**User's choice:** Excluir PC completamente
**Notes:** Juegos de PC instalados (Steam, etc.) tienen dependencias de registro y rutas absolutas que se rompen al mover. Solo se organizan ROMs de consola.

| Opción exclusiones adicionales | Seleccionado |
|-------------------------------|--------------|
| Solo las ya protegidas (SKIP_PATH_PARTS) | ✓ |
| Añadir más exclusiones | |

---

## Claude's Discretion

- Ámbito del escaneo al organizar (Series/Películas)
- Formato de rutas en rename_plan.tsv (absolutas vs relativas)
- Formato del resumen final (MENU-03)
- Estructura interna de módulos en organizer.py

## Deferred Ideas

None.

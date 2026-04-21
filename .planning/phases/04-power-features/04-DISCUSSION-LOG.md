# Phase 4: Power Features - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 04-power-features
**Areas discussed:** Qué detecta el generador

---

## Qué detecta el generador

| Option | Description | Selected |
|--------|-------------|----------|
| Solo series y películas | Detecta archivos de vídeo con formato incorrecto para series/películas. Usa RE_SERIES/RE_MOVIE existentes. | |
| Series, películas y juegos | También detecta archivos de juego fuera de Juegos\<sistema>\. | ✓ |
| Cualquier vídeo sin patrón reconocido | Lista todos los vídeos que no coinciden con ningún patrón, con new_path vacío como placeholder. | |

**User's choice:** Series, películas y juegos

---

| Option | Description | Selected |
|--------|-------------|----------|
| Solo normalizar lo reconocido | Si ya tiene los datos en formato distinto, propone el formato correcto. Si no reconoce, salta. Cero falsos positivos. | ✓ |
| Normalizar + listar no reconocidos | Normaliza lo que puede y añade al TSV los no reconocidos con new_path = old_path como placeholder. | |

**User's choice:** Solo normalizar lo reconocido

---

| Option | Description | Selected |
|--------|-------------|----------|
| Archivos de juego fuera de Juegos\ | Detecta archivos con extensiones de juego fuera de Juegos\<sistema>\ y propone moverlos. | ✓ |
| Solo nombres mal formateados en Juegos\ | Revisa archivos ya dentro de Juegos\ y detecta nombres incorrectos. | |

**User's choice:** Archivos de juego fuera de Juegos\

---

## Claude's Discretion

- Slot de menú para el generador: opción 6 (nueva)
- Formato del reporte de coherencia: consola + archivo coherence_report.txt
- Algoritmo de normalización para duplicados: strip año, tags de resolución, lowercase

## Deferred Ideas

- SxxExx como patrón primario → V2-01

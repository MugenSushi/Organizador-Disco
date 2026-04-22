# Phase 7 Plan: v2.1 — Series Sin Subcarpetas de Temporada

**Phase:** 07-v2.1-series-flat
**Wave:** 1
**Depends on:** Phase 6
**Files modified:** `organizer.py`, `.planning/REQUIREMENTS.md`
**Requirements addressed:** ORG-01 (modified)

## Objective

Cambiar la estructura de carpetas para series: todos los episodios van directamente en `Series\<Show>\` sin subcarpetas de `Temporada X`.

---

## Task 1: Modify organize_videos_and_games() — remove season subfolder

<read_first>
- `organizer.py` lines 531-548 (series detection and destination logic in organize_videos_and_games)
</read_first>

<action>

En la función `organize_videos_and_games()`, donde se maneja el match de series, cambiar:

**Antes (línea 539):**
```python
dst_dir = drive_root / "Series" / show / f"Temporada {season}"
```

**Después:**
```python
dst_dir = drive_root / "Series" / show
```

Esto elimina la subcarpeta "Temporada X" y coloca todos los episodios directamente en la carpeta de la serie.

</action>

<acceptance_criteria>

- La línea `dst_dir = drive_root / "Series" / show / f"Temporada {season}"` cambia a `dst_dir = drive_root / "Series" / show`
- Los episodios de series ya no se organizan en subcarpetas de temporada
- Películas siguen usando `Peliculas\<Titulo (Ano)>\` sin cambios
- El código compila sin errores (python -m py_compile)

---

## Task 2: Update ORG-01 in REQUIREMENTS.md

<read_first>
- `.planning/REQUIREMENTS.md` lines 34-35 (ORG-01)
</read_first>

<action>

Actualizar el texto de ORG-01 para reflejar el nuevo comportamiento:

**Antes:**
```
- [x] **ORG-01**: Los archivos de vídeo con patrón "Show - Temporada X - Episodio Y" se mueven a Series\<Show>\Temporada X\
```

**Después:**
```
- [x] **ORG-01**: Los archivos de vídeo con patrón "Show - Temporada X - Episodio Y" se mueven a Series\<Show>\ (todos los episodios juntos, sin subcarpetas de temporada)
```

</action>

<acceptance_criteria>

- ORG-01 en REQUIREMENTS.md refleja la estructura sin subcarpetas de temporada

---

## Task 3: Update ROADMAP.md Phase 7 status

<read_first>
- `.planning/ROADMAP.md` lines 24-38 (Phase 7 entry)
- `.planning/ROADMAP.md` lines 111-117 (Progress table)
</read_first>

<action>

En ROADMAP.md:
1. Cambiar Phase 7 de `- [ ]` a `- [x]`
2. Cambiar el plan de `- [ ] 07-01-PLAN.md` a `- [x] 07-01-PLAN.md`
3. En la tabla de progreso, cambiar Phase 7 a `1/1 | Completed | 2026-04-22`

</action>

<acceptance_criteria>

- Phase 7 marcado como completo en ROADMAP.md
- Tabla de progreso actualizada

---

## Task 4: Update STATE.md

<read_first>
- `.planning/STATE.md` (header and recent changes)
</read_first>

<action>

Actualizar STATE.md:
1. Cambiar `milestone` a `v2.1`
2. Cambiar `milestone_name` a `Series Flat Structure`
3. Añadir entrada en "Recent Changes" describiendo el cambio

</action>

<acceptance_criteria>

- STATE.md refleja milestone v2.1

---

## must_haves

1. Series episodes go to `Series\<Show>\` (no Temporada subfolder)
2. Movies still use `Peliculas\<Titulo (Ano)>\` unchanged
3. ORG-01 updated in REQUIREMENTS.md
4. ROADMAP.md Phase 7 marked complete

## Verification

1. `grep "Temporada" organizer.py` — should only find references in comments, not in the destination path logic
2. Read organize_videos_and_games and confirm series destination is `Series/<show>` without Temporada subfolder
3. REQUIREMENTS.md ORG-01 reflects new behavior
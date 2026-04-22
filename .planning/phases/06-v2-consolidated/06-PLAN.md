# Phase 6 Plan: v2 — Consolidated "Ordenar Todo"

**Phase:** 06-v2-consolidated
**Wave:** 1
**Depends on:** Phase 1, Phase 5
**Files modified:** `organizer.py`
**Requirements addressed:** V2-05, V2-06

## Objective

Consolidar el menú en una opción única "Ordenar todo" que ejecuta todas las operaciones de organización en secuencia.

---

## Task 1: Create organize_all() function

<read_first>
- `organizer.py` lines 511-558 (organize_videos_and_games)
- `organizer.py` lines 561-606 (organize_other_files)
- `organizer.py` lines 428-452 (_remove_empty_dirs)
- `organizer.py` lines 169-214 (Executor class)
</read_first>

<action>

Add a new function `organize_all()` in SECTION 13 (after `organize_other_files`) that:
1. Calls `organize_videos_and_games(executor, drive_root)` and accumulates counts
2. Calls `organize_other_files(executor, drive_root)` and accumulates counts
3. Calls `_remove_empty_dirs(drive_root, [])` for cleanup
4. Returns combined `counts` dict with all 3 operation results merged

```python
def organize_all(executor: Executor, drive_root: Path) -> dict:
    """Run all organization operations in sequence: videos/games, other files, empty cleanup."""
    counts = {"procesados": 0, "movidos": 0, "saltados": 0, "errores": 0}
    drive_root = Path(drive_root)

    # Step 1: videos and games
    counts1 = organize_videos_and_games(executor, drive_root)
    for k in counts:
        counts[k] += counts1.get(k, 0)

    # Step 2: other files (docs, PC games, software)
    counts2 = organize_other_files(executor, drive_root)
    for k in counts:
        counts[k] += counts2.get(k, 0)

    # Step 3: empty folder cleanup
    _remove_empty_dirs(drive_root, [])

    return counts
```

</action>

<acceptance_criteria>

- `organizer.py` contains `def organize_all(executor: Executor, drive_root: Path) -> dict:`
- The function calls `organize_videos_and_games`, `organize_other_files`, and `_remove_empty_dirs` in that order
- Returns a dict with keys: `procesados`, `movidos`, `saltados`, `errores`
- `_remove_empty_dirs` is called with an empty list for removed folders (intentionally discarded — cleanup is best-effort)

---

## Task 2: Update show_menu() to use new structure

<read_first>
- `organizer.py` lines 954-997 (show_menu function)
</read_first>

<action>

Replace the current show_menu() menu options with the new structure:

```python
print()
print(f"=== Organizador | {drive['root']} {drive['label']} ===")
print(" 1) Ordenar todo")
print(" 2) Aplicar rename_plan.tsv")
print(" 3) Revertir ultima operacion")
print(" 4) Detectar incoherencias")
print(f" 5) Dry-run: {dry_label}")
print(" 6) Generar rename_plan.tsv")
print(" 0) Salir")
```

Update the choice handling (elif chain):
- `choice == "1"`: call `organize_all(executor, Path(drive["root"]))`
- `choice == "2"`: rename apply_renames (same as old option 3)
- `choice == "3"`: undo_last_run (same as old option 4)
- `choice == "4"`: check_coherence (same as old option 5)
- `choice == "5"`: toggle dry-run (same as old option 6)
- `choice == "6"`: generate_rename_plan (same as old option 7)
- Remove handling for old options 1 and 2 entirely

</action>

<acceptance_criteria>

- Menu prints option "1) Ordenar todo" as the first option
- Selecting "1" calls `organize_all(executor, Path(drive["root"]))`
- Options 2-6 correspond to the old options 3-7
- No handling exists for choices "7" or invalid old options
- `organize_all` is called with `_prepare_executor_for_run` before it and `_flush_and_clear` after it (same pattern as other operations)

---

## Task 3: Update Requirements traceability

<read_first>
- `.planning/REQUIREMENTS.md` lines 55-63 (v2 requirements section)
</read_first>

<action>

Mark V2-05 and V2-06 as complete in the requirements file:
- Change `V2-05` from `- [ ]` to `- [x]`
- Change `V2-06` from `- [ ]` to `- [x]`

</action>

<acceptance_criteria>

- REQUIREMENTS.md shows V2-05 and V2-06 with `[x]` checked
- Traceability table at bottom of REQUIREMENTS.md has Phase 6 entries for V2-05 and V2-06 marked Complete

---

## Task 4: Update ROADMAP.md

<read_first>
- `.planning/ROADMAP.md` lines 27-34 (Phase 6 details)
- `.planning/ROADMAP.md` lines 109-116 (Progress table)
</read_first>

<action>

In ROADMAP.md:
1. Change Phase 6 from `- [ ]` to `- [x]`
2. Change Phase 6 Plans entry from `- [ ] 06-01-PLAN.md` to `- [x] 06-01-PLAN.md`
3. In the Progress table, update Phase 6 row to `1/1 | Completed | 2026-04-22`

</action>

<acceptance_criteria>

- ROADMAP.md Phase 6 marked as complete with `[x]`
- Progress table shows Phase 6: 1/1, Completed, 2026-04-22

---

## Task 5: Update STATE.md

<read_first>
- `.planning/STATE.md`
</read_first>

<action>

Update STATE.md:
1. Set `status` to `complete`
2. Set `milestone` to `v2.0`
3. Set `milestone_name` to `Consolidated Menu`
4. Update `last_updated` to current timestamp
5. Add entry under "Recent Changes" describing the v2 consolidation

</action>

<acceptance_criteria>

- STATE.md shows milestone: v2.0, status: complete
- "Recent Changes" section includes v2 consolidation entry with today's date

---

## must_haves

1. Single "Ordenar todo" option in menu executes all organization operations
2. Menu has exactly 6 numbered options + exit (1-6, 0)
3. V2-05 and V2-06 marked complete in REQUIREMENTS.md
4. ROADMAP.md Phase 6 marked complete
5. STATE.md updated to reflect v2.0 completion

## Verification

1. Read `organizer.py` and confirm `organize_all` function exists and calls the 3 operations
2. Read `show_menu` and confirm menu structure is: 1=Ordenar todo, 2=Aplicar renames, 3=Undo, 4=Coherence, 5=Dry-run, 6=Generar rename plan, 0=Exit
3. Run `organizer.py` in dry-run mode and verify the "Ordenar todo" option appears first
4. Confirm REQUIREMENTS.md, ROADMAP.md, and STATE.md all reflect v2 changes
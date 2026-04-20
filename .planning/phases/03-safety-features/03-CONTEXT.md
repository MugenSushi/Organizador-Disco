# Phase 3: Safety Features - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 wires undo into the menu: each menu-option execution writes an atomic JSON log, and option 3 reverts the last log. At the end of this phase the user can confidently undo any organize or rename operation from the menu.

TSV generation and coherence checking are NOT in scope — those land in Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Undo log scope (UNDO-01, UNDO-02, UNDO-03)

- **D-01:** One "undoable run" = one menu-option execution. Organize (option 1) writes its own log; Apply renames (option 2) writes its own log. Undo (option 3) reverts whichever was last.
- **D-02:** Keep only the latest log. File name: `last_run.json` in `_organizer_logs\`. Always overwritten on the next operation. Covers UNDO-03 exactly — no history beyond last run needed.
- **D-03:** Log format (top-level object):
  ```json
  {
    "serial": 1234567890,
    "drive_root": "F:\\",
    "timestamp": "2026-04-20T14:30:00",
    "moves": [
      {"src": "Series\\Show\\S01E01.mkv", "dst": "...", "ts": "..."}
    ]
  }
  ```
  Paths stored **relative to drive_root** so the log survives drive-letter changes (UNDO-02). Serial number used to re-anchor to the correct drive if letter changed.
- **D-04:** Undo conflict handling — when reverting and the expected destination file no longer exists (moved elsewhere), skip that entry and continue. Print a summary of skipped entries at the end (count + list). Never abort mid-revert.

### Claude's Discretion

- Exact field names within the JSON log entries (`src`, `dst`, `ts` or similar) — follow CLAUDE.md `{src, dst, timestamp}` convention.
- Whether to write the log atomically (write to `.tmp` then rename) or direct-write — atomic preferred to avoid corrupt logs on crash.
- How to display undo progress (silent per-file or single summary line) — single summary line consistent with `_print_summary()` pattern from Phase 2.
- Whether dry-run suppresses log writing entirely (no moves → nothing to undo) or writes an empty log — suppress is cleaner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/REQUIREMENTS.md` — UNDO-01, UNDO-02, UNDO-03
- `.planning/PROJECT.md` — Core value, constraints
- `CLAUDE.md` — json undo log pattern: `{src, dst, timestamp}`, `json.dump(indent=2, ensure_ascii=False)`

### Prior phase artifacts
- `.planning/phases/01-infrastructure/01-CONTEXT.md` — D-01..D-03 drive selection, serial already collected
- `.planning/phases/02-core-operations/02-CONTEXT.md` — D-01..D-03 dry-run toggle, summary format
- `organizer.py` — Current code: `Executor.move()`, `show_menu()` (option 3 stub), `drive['serial']`, `LOG_DIR_NAME`

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Executor.move(src, dst)` — all moves pass through here; undo log writes must hook in here or at call sites
- `drive['serial']` — already available from `get_removable_drives()`, passed into `show_menu()`
- `LOG_DIR_NAME = "_organizer_logs"` — established log directory constant
- `json` — already imported at module level
- `_print_summary(counts)` — pattern for end-of-operation one-liner; undo should follow same style
- `show_menu()` — option 3 stub already present: `print("(Disponible en Fase 3)")`

### Established Patterns
- `json.dump(indent=2, ensure_ascii=False)` for human-readable logs (CLAUDE.md)
- `shutil.move(str(src), str(final_dst))` for all moves
- Summary displayed with `_print_summary()` before returning to menu

### Integration Points
- `Executor.move()` must record each successful move to the current-run log accumulator
- `show_menu()` option 3 must call the new undo function
- Log must be flushed atomically at end of each operation (option 1 or 2 completes)

</code_context>

<specifics>
## Specific Ideas

- Log file: `<drive>\_organizer_logs\last_run.json` — always overwritten, never rotated
- Undo conflict: skip + count, print list of skipped files after revert completes
- Dry-run: suppress log writing (no real moves → nothing to undo)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-safety-features*
*Context gathered: 2026-04-20*

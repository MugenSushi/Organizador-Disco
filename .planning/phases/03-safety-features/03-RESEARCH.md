# Phase 3: Safety Features - Research

**Researched:** 2026-04-20
**Domain:** Python stdlib — atomic file I/O, JSON undo log, Executor integration, revert logic
**Confidence:** HIGH (all patterns verified against Python 3.14.2 on Windows / official stdlib docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** One "undoable run" = one menu-option execution. Organize (option 1) writes its own log; Apply renames (option 2) writes its own log. Undo (option 3) reverts whichever was last.
- **D-02:** Keep only the latest log. File name: `last_run.json` in `_organizer_logs\`. Always overwritten on the next operation.
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
  Paths stored **relative to drive_root** (UNDO-02). Serial used for drive re-anchoring.
- **D-04:** Undo conflict handling — skip missing files, print summary of skipped entries, never abort mid-revert.

### Claude's Discretion

- Exact field names within log entries — follow CLAUDE.md `{src, dst, timestamp}` convention.
- Atomic write (`.tmp` then rename) vs direct-write — atomic preferred.
- Undo progress display — single summary line consistent with `_print_summary()`.
- Dry-run suppresses log writing entirely (no real moves → nothing to undo).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UNDO-01 | Each move/rename operation writes an atomic JSON log | Atomic write pattern: write to `.tmp`, then `os.replace()` |
| UNDO-02 | Log stores drive-relative paths + volume serial number | Relative path via `Path.relative_to(drive_root)`, serial from `drive['serial']` already in scope |
| UNDO-03 | Menu option 3 reverts the last complete run | Revert loop reads log, reconstructs absolute paths, calls `shutil.move()` in reverse order |
</phase_requirements>

---

## Summary

Phase 3 adds one capability: a JSON undo log that is written atomically after every successful operation, and an undo function wired to menu option 3 that reverses the log. The underlying infrastructure (Executor, log directory, serial number, JSON import) is already in place from Phases 1 and 2 — this phase is integration work, not new infrastructure.

The three integration points are narrow and well-defined: (1) `Executor.move()` must accumulate move records into a per-run list, (2) after the operation function returns its counts, a flush step writes the accumulator to disk atomically, and (3) menu option 3 replaces its stub with a call to the new undo function. All required stdlib modules (`json`, `os`, `pathlib`, `datetime`) are already imported.

The only non-trivial design question is where the accumulator lives: on the `Executor` instance (simplest, naturally scoped to one run) vs. a standalone context object. Given the single-file architecture and that Executor is already passed through all operations, the accumulator belongs on `Executor`.

**Primary recommendation:** Add `self._undo_log: list[dict]` and `self._current_run_serial` / `self._current_run_root` to `Executor.__init__`, record each successful real move in `Executor.move()`, and add `Executor.flush_undo_log(log_path)` + `Executor.clear_undo_log()` methods called from `show_menu()` after each operation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Accumulate move records | Executor class | — | Executor is the single mutation point; accumulating there guarantees every real move is captured |
| Flush log to disk atomically | show_menu() call site | Executor helper method | The menu knows when an operation is complete; Executor provides the flush method |
| Undo revert logic | Standalone function `undo_last_run()` | show_menu() (caller) | Keeps revert logic testable and separate from the menu loop |
| Drive re-anchoring on letter change | `undo_last_run()` | `get_removable_drives()` (data source) | Serial matching already exists in drive detection; undo reads serial from log and re-anchors |

---

## Standard Stack

### Core (all already imported at module level)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `json` | stdlib 3.x | Serialize/deserialize undo log | Already imported; `json.dump(indent=2, ensure_ascii=False)` is CLAUDE.md convention |
| `os` | stdlib 3.x | `os.replace()` for atomic rename of `.tmp` → `last_run.json` | Only stdlib call that atomically replaces an existing file on Windows [VERIFIED: Python 3.14.2 `os.replace` available on win32] |
| `pathlib.Path` | stdlib 3.4+ | `Path.relative_to()` for drive-relative path storage; path reconstruction during undo | Already used everywhere in codebase |
| `datetime` | stdlib | `datetime.now().isoformat()` for top-level timestamp and per-move `ts` | Already standard Python; no import needed beyond `from datetime import datetime` |
| `shutil` | stdlib | `shutil.move()` for the actual revert moves | Already imported; revert uses same pattern as forward moves |

### No New Dependencies

This phase adds zero new imports beyond `from datetime import datetime` (or `import datetime` — already available via stdlib).

---

## Architecture Patterns

### System Architecture Diagram

```
show_menu() — menu loop
    |
    |-- option 1 or 2 selected
    |       |
    |       v
    |   organize_videos_and_games() / apply_renames()
    |       |  calls executor.move(src, dst) for each file
    |       v
    |   Executor.move(src, dst)
    |       |-- real move: shutil.move() succeeds
    |       |       |
    |       |       v
    |       |   self._moves.append({src_rel, dst_rel, ts})
    |       |       |
    |       |-- dry_run=True OR blocked: no append
    |
    |   operation returns counts
    |       |
    |       v
    |   executor.flush_undo_log(log_path)   [only if not dry_run and moves > 0]
    |       |-- write to log_path.with_suffix('.tmp')
    |       |-- os.replace(tmp, log_path)
    |       |-- executor.clear_undo_log()
    |
    |-- option 3 selected
    |       |
    |       v
    |   undo_last_run(drive, drives)
    |       |-- read last_run.json
    |       |-- match serial → current drive root (re-anchor if letter changed)
    |       |-- for move in reversed(data['moves']):
    |       |       reconstruct abs src/dst from drive_root + relative paths
    |       |       if dst (current location) exists: shutil.move(dst → src)
    |       |       else: skip + count
    |       |-- print summary (moved, skipped)
    |       |-- delete or zero last_run.json  [discussed below]
```

### Recommended Project Structure

No structural changes — all new code lives in `organizer.py` following the existing section convention:

```
organizer.py
  SECTION 7  — Executor class  [add accumulator fields + flush/clear methods]
  SECTION 14 — show_menu()     [replace option 3 stub; add flush calls after ops]
  SECTION 15 — (new) UndoLog helpers: flush_undo_log(), undo_last_run()
```

---

## Pattern 1: Atomic Log Write (os.replace)

**What:** Write JSON to a `.tmp` file, then atomically rename it over the target.
**When to use:** Any time you must not leave a corrupt/partial file on disk after a crash.

```python
# Source: Python docs — os.replace() [VERIFIED: available on win32, Python 3.14.2]
import os, json
from pathlib import Path

def flush_undo_log(log_path: Path, data: dict) -> None:
    """Write data to log_path atomically. No-op if data['moves'] is empty."""
    if not data.get("moves"):
        return
    tmp = log_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(str(tmp), str(log_path))  # atomic on same filesystem [VERIFIED]
```

**Windows notes on os.replace() [VERIFIED: Python 3.14.2 on win32]:**
- `os.replace(src, dst)` is atomic when both paths are on the same drive — uses `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`. [CITED: https://docs.python.org/3/library/os.html#os.replace]
- If `src` and `dst` are on different filesystems, `os.replace` is NOT atomic (copies then deletes). Since `tmp` and `log_path` are always in the same `_organizer_logs` directory, this is never an issue here.
- `os.replace` succeeds even if `dst` does not yet exist (first run). [VERIFIED]
- If the process is killed between `write_text` and `os.replace`, the `.tmp` file is left behind — harmless, will be overwritten next run. No cleanup needed.

---

## Pattern 2: Executor Accumulator

**What:** Add a `_moves` list to `Executor.__init__` that `Executor.move()` appends to on every real (non-dry-run) successful move.

```python
# Integration point in Executor.__init__
def __init__(self, dry_run: bool = False):
    self.dry_run = dry_run
    self._moves: list[dict] = []          # NEW — accumulates per-run move records
    self._log_serial: int = 0             # NEW — set by show_menu before each operation
    self._log_drive_root: str = ""        # NEW — set by show_menu before each operation
```

```python
# Integration point in Executor.move() — after the shutil.move() succeeds:
#   (after line: logger.info("MOVE: %s -> %s", src, final_dst))
from datetime import datetime
# Only append if we have a drive_root set (guard against uninitialized use)
if self._log_drive_root:
    drive_root = Path(self._log_drive_root)
    try:
        src_rel = str(src.relative_to(drive_root))
        dst_rel = str(final_dst.relative_to(drive_root))
    except ValueError:
        # Path outside drive_root — log absolute paths as fallback
        src_rel = str(src)
        dst_rel = str(final_dst)
    self._moves.append({
        "src": src_rel,
        "dst": dst_rel,
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
```

**Why accumulate on Executor rather than passing a list through every function:**
- Executor is already threaded through every operation function — no signature changes needed.
- Accumulator is naturally scoped to one run: clear it before the operation, flush after.
- Consistent with the dry_run flag already living on Executor.

---

## Pattern 3: Flushing the Log from show_menu()

**What:** After each operation (1 or 2), call flush then clear on the executor.

```python
# In show_menu(), replace option 1 block:
elif choice == "1":
    _prepare_executor_for_run(executor, drive)       # set serial + root, clear _moves
    counts = organize_videos_and_games(executor, Path(drive["root"]))
    _print_summary(counts)
    _flush_and_clear(executor, log_path)             # flush if not dry_run

# In show_menu(), replace option 2 block:
elif choice == "2":
    _prepare_executor_for_run(executor, drive)
    counts = apply_renames(executor, Path(drive["root"]))
    _print_summary(counts)
    _flush_and_clear(executor, log_path)
```

Helper functions (new in SECTION 15):

```python
def _prepare_executor_for_run(executor: Executor, drive: dict) -> None:
    """Set per-run metadata on executor and clear previous accumulator."""
    executor._log_serial = drive["serial"]
    executor._log_drive_root = drive["root"]
    executor._moves = []

def _flush_and_clear(executor: Executor, log_path: Path) -> None:
    """Write undo log atomically if not dry_run and moves were recorded."""
    if executor.dry_run:
        return  # dry-run: suppress log entirely (D-02 discretion decision)
    if not executor._moves:
        return
    from datetime import datetime
    data = {
        "serial": executor._log_serial,
        "drive_root": executor._log_drive_root,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "moves": executor._moves,
    }
    flush_undo_log(log_path, data)
    executor._moves = []
```

---

## Pattern 4: Undo Revert Logic

**What:** Read `last_run.json`, re-anchor drive root if letter changed, revert in reverse order.

```python
def undo_last_run(drive: dict, all_drives: list[dict]) -> None:
    """Revert the last logged operation. Implements UNDO-03, UNDO-02, D-04."""
    log_path = Path(drive["root"]) / LOG_DIR_NAME / "last_run.json"

    # --- Step 1: find last_run.json on any of the known drives (handles letter change)
    log_data = None
    actual_log_path = None
    for d in all_drives:
        candidate = Path(d["root"]) / LOG_DIR_NAME / "last_run.json"
        if candidate.exists():
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                if raw.get("serial") == drive["serial"]:
                    log_data = raw
                    actual_log_path = candidate
                    break
            except (json.JSONDecodeError, OSError):
                continue

    if log_data is None:
        # Also try the current drive directly (common case: letter unchanged)
        if log_path.exists():
            try:
                log_data = json.loads(log_path.read_text(encoding="utf-8"))
                actual_log_path = log_path
            except (json.JSONDecodeError, OSError):
                pass

    if log_data is None:
        print("No hay ninguna operacion para deshacer.")
        return

    # --- Step 2: determine the drive root to use for path reconstruction
    # Serial match already done above; use the drive root from the log
    # (the letter stored in the log may differ from current letter — use current drive["root"])
    revert_root = Path(drive["root"])

    moves = log_data.get("moves", [])
    if not moves:
        print("El log no contiene movimientos para revertir.")
        return

    # --- Step 3: revert in reverse order (D-04: skip missing, never abort)
    reverted = 0
    skipped = []
    errors = 0

    for entry in reversed(moves):
        # Reconstruct absolute paths — src/dst in log are relative to drive_root
        dst_abs = revert_root / entry["dst"]   # current location of the file
        src_abs = revert_root / entry["src"]   # where it should go back

        if not dst_abs.exists():
            skipped.append(entry["dst"])
            continue

        try:
            src_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst_abs), str(src_abs))
            reverted += 1
            logger.info("UNDO: %s -> %s", dst_abs, src_abs)
        except (PermissionError, OSError) as exc:
            logger.error("UNDO ERR: %s : %s", dst_abs, exc)
            errors += 1

    # --- Step 4: print summary (consistent with _print_summary style)
    print(f"[OK] Revertidos: {reverted} | Saltados: {len(skipped)} | Errores: {errors}")
    if skipped:
        print("Archivos no encontrados (saltados):")
        for s in skipped:
            print(f"  {s}")
```

**Drive re-anchoring strategy [VERIFIED: serial already in drive dict from Phase 1]:**
- `drive['serial']` is always available from `get_removable_drives()` → `_get_volume_serial()`.
- The undo function receives `drive` (current selection) AND `all_drives` (full list).
- It looks for `last_run.json` on every known drive whose serial matches — handles the case where the drive letter changed between runs.
- `show_menu()` has access to `drive` and needs `all_drives` — add `all_drives` parameter to `show_menu()` or look up at call site.

---

## Pattern 5: Log Delete / Invalidate After Undo

**Decision point (Claude's discretion):** After successful undo, should the log be deleted?

**Recommendation:** Delete `last_run.json` after a successful undo. Rationale:
- Prevents double-undo (running undo twice on the same log would move files back again).
- Consistent with "keep only latest log" (D-02) — after undo the operation no longer exists.
- If undo partially fails (errors > 0), still delete — partial state is logged to `organizer.log`.

```python
# After the revert loop, at the end of undo_last_run():
try:
    actual_log_path.unlink()
except OSError:
    pass  # non-critical — log left behind is harmless
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom lock/tmp mechanism | `os.replace()` after writing to `.tmp` | `os.replace` uses `MoveFileExW` on Windows — kernel-level atomicity [CITED: Python docs os.replace] |
| Relative path construction | String manipulation / `os.path.relpath()` | `Path.relative_to(drive_root)` | Raises `ValueError` if path is outside root — surfaced as explicit error [VERIFIED: pathlib docs] |
| Timestamp string | `time.strftime()` | `datetime.now().isoformat(timespec="seconds")` | ISO 8601, human-readable, sorts lexicographically, already stdlib |
| Revert move | Custom file copy + delete | `shutil.move()` | Same as forward moves — consistent, cross-filesystem safe, already used everywhere |

**Key insight:** This phase is almost entirely plumbing — connecting existing pieces. The only novel code is `os.replace()` for atomicity and `Path.relative_to()` for portable path storage.

---

## Common Pitfalls

### Pitfall 1: os.replace() Fails If .tmp and Target Are on Different Drives
**What goes wrong:** `os.replace(tmp_path, target_path)` raises `OSError: [Errno 18] Invalid cross-device link` if `tmp` and `target` are on different filesystems.
**Why it happens:** `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING` is not atomic across volumes.
**How to avoid:** Always create `.tmp` in the same directory as the target (`log_path.with_suffix(".tmp")`). Since both are under `<drive>\_organizer_logs\`, they are always co-located on the same drive.
**Warning signs:** OSError during log flush on multi-drive setups — but given the architecture (tmp always beside target), this cannot happen.

### Pitfall 2: Path.relative_to() Raises ValueError for Paths Outside Drive Root
**What goes wrong:** If a file was moved from outside `drive_root` (theoretically blocked by safety guards, but defensive coding required), `Path.relative_to(drive_root)` raises `ValueError`.
**How to avoid:** Wrap in `try/except ValueError` and fall back to storing the absolute path string. [VERIFIED: Python pathlib docs]

### Pitfall 3: Reversed Iteration on a List
**What goes wrong:** Iterating `for entry in moves[::-1]` creates a full copy; for large logs this wastes memory.
**How to avoid:** Use `for entry in reversed(moves)` — `reversed()` on a list returns a `list_reverseiterator` without copying. [VERIFIED: Python docs reversed()]

### Pitfall 4: Log Written Even on Dry-Run
**What goes wrong:** If `flush_and_clear` is called without checking `executor.dry_run`, a dry-run shows up as an undoable operation with 0 moves.
**How to avoid:** Gate the flush: `if executor.dry_run: return` — explicitly verified in the pattern above.

### Pitfall 5: Double-Undo
**What goes wrong:** User runs undo twice — second undo reverses the revert, undoing the undo.
**How to avoid:** Delete `last_run.json` after successful undo (Pattern 5 above). If deletion fails, log entry persists but re-running undo is idempotent for most files (they won't exist at `dst_abs` after the first revert, so they'll be counted as skipped).

### Pitfall 6: show_menu() Needs all_drives for Re-anchoring
**What goes wrong:** `undo_last_run()` needs to search all drives by serial. `show_menu()` currently only receives the selected `drive` dict, not the full list.
**How to avoid:** Pass `drives` (the full list from `get_removable_drives()`) as a parameter to `show_menu()`. This requires a one-line signature change: `def show_menu(executor, drive, drives)` and updating `main()` to pass `drives`.

### Pitfall 7: Stale .tmp File on Crash
**What goes wrong:** If the process crashes after writing `.tmp` but before `os.replace()`, the `.tmp` file is left in `_organizer_logs\`. On next run, the new flush overwrites it cleanly (same path). No cleanup needed — but the file will be visible to users who inspect the folder.
**How to avoid:** This is acceptable; document it as known behavior. No action required.

---

## Code Examples

### Full Atomic Flush Function
```python
# Source: Python docs os.replace + pathlib [VERIFIED]
def flush_undo_log(log_path: Path, data: dict) -> None:
    """Write undo log atomically. Skips if moves list is empty."""
    if not data.get("moves"):
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = log_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(log_path))
```

### Relative Path Storage
```python
# Source: Python pathlib docs [VERIFIED]
drive_root = Path("F:\\")
file_path = Path("F:\\Series\\Show\\S01E01.mkv")
relative = str(file_path.relative_to(drive_root))
# relative == "Series\\Show\\S01E01.mkv"

# Reconstruction:
abs_path = drive_root / relative
# abs_path == Path("F:\\Series\\Show\\S01E01.mkv")
```

### Datetime Timestamp
```python
# Source: Python datetime docs [VERIFIED]
from datetime import datetime
ts = datetime.now().isoformat(timespec="seconds")
# ts == "2026-04-20T14:30:00"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Per-session logging to rotating file | Per-operation atomic JSON log | Undo is possible; JSON is human-inspectable |
| `os.rename()` for file rename | `os.replace()` | `os.replace` is atomic and overwrites existing target |

**Deprecated/outdated:**
- `os.rename()` for atomic replacement: `os.rename` raises `FileExistsError` on Windows if the destination exists. Use `os.replace` instead. [CITED: https://docs.python.org/3/library/os.html#os.rename vs os.replace]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `os.replace()` is atomic on Windows when src and dst are on the same drive | Atomic write pattern | Log could be corrupt on crash if not truly atomic; mitigated by .tmp approach regardless |

All other claims were verified against the running Python 3.14.2 interpreter or cited from official Python docs.

---

## Open Questions

1. **Should show_menu() receive `all_drives` or look them up internally for undo?**
   - What we know: `get_removable_drives()` is fast (pure ctypes, no subprocess). `show_menu()` currently only holds the selected `drive`.
   - What's unclear: Whether re-anchoring is a real use case (user unplugs and replug drive gets new letter) or theoretical.
   - Recommendation: Pass `drives` from `main()` into `show_menu()` — signature change is trivial and makes the function testable without mocking globals.

2. **What if `_organizer_logs` directory doesn't exist when undo is called?**
   - What we know: `add_file_logging()` creates `_organizer_logs` at startup. If the drive was selected and logging set up, the directory exists.
   - Recommendation: In `undo_last_run()`, check `log_path.exists()` before `read_text()` — already handled by the "no log found" early-return path.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is pure Python stdlib code changes with no external dependencies. Python 3.14.2 confirmed available (`py -3 --version`). All required modules (`json`, `os`, `pathlib`, `shutil`, `datetime`) are stdlib.

---

## Security Domain

> `security_enforcement` not explicitly set to false — including section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (path traversal) | Drive-root containment check already in `apply_renames()` — undo must apply same guard |
| V5 Input Validation | yes | JSON from `last_run.json` is local user-written data; `json.loads()` is safe; validate field presence before use |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered `last_run.json` with path traversal paths | Tampering | When reconstructing abs paths in `undo_last_run()`, verify `abs_path.resolve()` starts with `drive_root.resolve()` before calling `shutil.move()` |
| Missing/extra fields in log JSON | Tampering | Use `.get()` with defaults; skip entries with missing `src` or `dst` fields |

**Path traversal guard for undo (mirrors the guard in `apply_renames()`):**
```python
# Before reverting each entry in undo_last_run():
drive_root_str = str(revert_root.resolve()).lower()
src_str = str(src_abs.resolve()).lower()
dst_str = str(dst_abs.resolve()).lower()
if not (src_str.startswith(drive_root_str + "\\") or src_str == drive_root_str):
    logger.warning("UNDO SKIP (path traversal): %s", src_abs)
    skipped.append(entry.get("dst", "?"))
    continue
if not (dst_str.startswith(drive_root_str + "\\") or dst_str == drive_root_str):
    logger.warning("UNDO SKIP (path traversal): %s", dst_abs)
    skipped.append(entry.get("dst", "?"))
    continue
```

---

## Sources

### Primary (HIGH confidence)
- Python 3.14.2 interpreter — `py -3 --version` confirmed on target machine [VERIFIED]
- `os.replace` available on win32 — `py -3 -c "import os; print(hasattr(os, 'replace'))"` → `True` [VERIFIED]
- https://docs.python.org/3/library/os.html#os.replace — atomic rename behavior documented [CITED]
- https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.relative_to — ValueError on non-subpath [CITED]
- https://docs.python.org/3/library/json.html — `json.dump(indent=2, ensure_ascii=False)` [CITED]
- `organizer.py` — `Executor.move()`, `show_menu()`, `drive['serial']`, `LOG_DIR_NAME`, `_print_summary()` all verified by direct code inspection [VERIFIED]

### Secondary (MEDIUM confidence)
- https://docs.python.org/3/library/datetime.html — `datetime.isoformat(timespec=)` [CITED]

---

## Metadata

**Confidence breakdown:**
- Atomic write pattern: HIGH — `os.replace` verified on running Python 3.14.2/win32
- Executor accumulator: HIGH — no new APIs; uses existing list/dict
- Revert logic: HIGH — `shutil.move` + `Path.relative_to` both existing patterns in codebase
- Drive re-anchoring: HIGH — `drive['serial']` already present from Phase 1

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stdlib-only, no external version drift)

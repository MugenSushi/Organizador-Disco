---
phase: 03-safety-features
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - organizer.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-21
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed the Phase 03 additions to `organizer.py`: the `Executor._moves` accumulator, `flush_undo_log()`,
`_prepare_executor_for_run()`, `_flush_and_clear()`, `undo_last_run()`, and `show_menu()` wiring.
The atomic write pattern is correct and the path traversal guard in `undo_last_run()` mirrors the
established `apply_renames()` pattern well. Three logic issues were found: a drive-letter re-anchor
failure for absolute-path log entries, a fallback block that can load a mismatched-serial log, and
a `.tmp` file leak on `OSError`. Two info items cover minor code clarity.

---

## Warnings

### WR-01: Absolute-path fallback in move() breaks undo when drive letter changes

**File:** `organizer.py:170-175`

**Issue:** When `src.relative_to(drive_root)` raises `ValueError` (path is not under `drive_root`),
`move()` stores the raw absolute strings as `src_rel`/`dst_rel` in the log (e.g. `E:\Videos\movie.mkv`).
In `undo_last_run()` these strings are re-joined with `revert_root /` (lines 622-623).
On Windows, `Path("F:\\") / "E:\\Videos\\movie.mkv"` returns `Path("E:\\Videos\\movie.mkv")` because
the right operand is an absolute path — the new root is silently discarded.
The path traversal guard then correctly rejects the entry, so no cross-drive damage occurs,
but **every move whose src/dst fell outside the drive root is silently skipped during undo**,
with no log entry distinguishing "skipped because missing" from "skipped because absolute path".

The guard condition (line 635) correctly protects against path traversal, so there is no security
risk, but affected files are permanently un-revertable after a drive-letter change.

**Fix:** If `relative_to()` fails, skip accumulating the entry entirely (these paths are anomalous
and should not be logged as revertable), and emit a warning:

```python
# In move(), replace lines 170-180:
try:
    src_rel = str(src.relative_to(drive_root))
    dst_rel = str(final_dst.relative_to(drive_root))
    self._moves.append({
        "src": src_rel,
        "dst": dst_rel,
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
except ValueError:
    logger.warning(
        "UNDO-SKIP: src or dst outside drive root — not logged for undo: %s -> %s",
        src, final_dst,
    )
```

---

### WR-02: Fallback in undo_last_run() loads log without serial verification

**File:** `organizer.py:587-595`

**Issue:** After the serial-matched loop (lines 575-585) finds nothing, the fallback block
(lines 587-595) reads `last_run.json` from the currently selected drive without checking
`raw.get("serial") == drive["serial"]`. This means if the serial-match loop exhausted all
candidates and found no match, the fallback will still load and act on a log from a drive whose
serial does not match the selected drive — the same guard that prevents false matches in the loop
is absent in the fallback.

In practice this rarely matters because: (a) the selected `drive` is always in `all_drives`, so
the loop already checks the current drive with serial validation; (b) the fallback is therefore
only reachable if `drive` is somehow absent from `all_drives` (which should not happen given
`show_menu`'s call chain). However, if those invariants ever break, the fallback silently undoes a
wrong log.

**Fix:** Add the serial check to the fallback, or — cleaner — remove the fallback entirely since
it is logically redundant (the current drive is always in `all_drives`):

```python
# Option A: remove the fallback block entirely (lines 587-595).
# The current drive is always in all_drives; the loop covers it with serial validation.

# Option B: add serial check if keeping fallback for defensive reasons:
if log_data is None:
    fallback = Path(drive["root"]) / LOG_DIR_NAME / "last_run.json"
    if fallback.exists():
        try:
            raw = json.loads(fallback.read_text(encoding="utf-8"))
            if raw.get("serial") == drive["serial"]:   # <-- add this guard
                log_data = raw
                actual_log_path = fallback
        except (json.JSONDecodeError, OSError):
            pass
```

---

### WR-03: .tmp file leaked on OSError in flush_undo_log()

**File:** `organizer.py:534-540`

**Issue:** `flush_undo_log()` writes to a `.tmp` file (line 535) and then calls `os.replace()` to
atomically swap it into place (line 536). If `os.replace()` raises `OSError` (e.g., cross-device
link error, which cannot happen on the same drive, but also disk-full during the rename),
the exception is caught and logged (lines 539-540) but the `.tmp` file is left on disk.
On subsequent successful runs the same `.tmp` path is overwritten, so the leak usually self-heals,
but a failed-then-abandoned session leaves a stale `.tmp` in `_organizer_logs\`.

**Fix:** Clean up the tmp file in the `OSError` handler:

```python
except OSError as exc:
    logger.error("ERR escribiendo log de undo: %s", exc)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
```

---

## Info

### IN-01: _flush_and_clear() clears _moves even when flush_undo_log() silently no-ops

**File:** `organizer.py:550-563`

**Issue:** `_flush_and_clear()` calls `flush_undo_log()` and then unconditionally clears
`executor._moves = []` (line 563). `flush_undo_log()` can silently return without writing the
log on `PermissionError` (line 537-538). In that case `_moves` is still cleared, so the data
is lost and a subsequent "Revertir" attempt will print "No hay ninguna operacion para deshacer."
rather than retrying or warning the user that undo data was not persisted.

This is an acceptable trade-off for read-only media, but the behavior is invisible to the user.
A one-line print after the warning in `flush_undo_log` would make it explicit.

**Fix (optional):** In `flush_undo_log()`, after the `PermissionError` warning, also print to
console so the user knows undo will not be available:

```python
except PermissionError:
    logger.warning("No se pudo escribir el log de undo (disco de solo lectura).")
    print("[!] Undo no disponible: disco de solo lectura.")
```

---

### IN-02: show_menu() docstring describes D-01/D-02 which are drive-selection decisions, not menu decisions

**File:** `organizer.py:675-676`

**Issue:** The docstring for `show_menu()` reads:
`"Option 5 toggles dry-run (D-01). No confirmation on operation with dry-run (D-02)."`
D-01 and D-02 in the project context refer to drive-selection decisions (auto-select single drive,
no retry on no drives). The dry-run toggle and confirmation behavior are not decision codes that
map to D-01/D-02. The docstring references the wrong decision codes, which could confuse future
readers cross-referencing the planning docs.

**Fix:** Remove or correct the decision-code references:

```python
def show_menu(executor: Executor, drive: dict, drives: list[dict]) -> None:
    """Numbered main menu. Option 5 toggles dry-run mode."""
```

---

_Reviewed: 2026-04-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

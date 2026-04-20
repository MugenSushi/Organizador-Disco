---
phase: 02-core-operations
fixed_at: 2026-04-20T14:47:33Z
review_path: .planning/phases/02-core-operations/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-20T14:47:33Z
**Source review:** .planning/phases/02-core-operations/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03 — fix_scope: critical_warning)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01 + WR-03: Relative paths in TSV resolve against CWD / `is_relative_to` Python 3.9 only

**Files modified:** `organizer.py`
**Commit:** 2076492
**Applied fix:**

WR-01 and WR-03 were fixed together in a single commit since they are in the same code block inside `apply_renames`.

- **WR-01:** Replaced bare `Path(old_str)` / `Path(new_str)` with relative-path anchoring:
  if the raw path is not absolute, it is prefixed with `drive_root` before any existence check
  or resolution. This ensures relative TSV paths such as `Videos\pelicula.mkv` resolve correctly
  against the selected drive rather than the Python process CWD.

- **WR-03:** Replaced the `Path.is_relative_to(drive_root.resolve())` calls (Python 3.9+) with
  a string-prefix comparison that works on Python 3.6+:
  ```python
  drive_root_str = str(drive_root.resolve()).lower()
  src_str_low.startswith(drive_root_str + "\\") or src_str_low == drive_root_str
  ```
  This avoids an `AttributeError` crash on older Python installs while preserving the same
  path-traversal containment semantics.

---

### WR-02: ROM-blocked files in `_organize_games` counted as errors

**Files modified:** `organizer.py`
**Commit:** c2b9df9
**Applied fix:**

Added an explicit `is_no_touch` check before calling `executor.move` inside the `_organize_games`
loop. Files with blocked extensions (`.gba`, `.iso`, `.bin`, etc.) are now routed to
`counts["saltados"]` with an `INFO` log entry rather than being passed to `executor.move` and
returned as `counts["errores"]`. A comment explains why the pre-check is necessary:
`executor.move` returns `None` for both hard-block skips and genuine OS errors, so call-site
disambiguation is required to produce an accurate error count.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-04-20T14:47:33Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

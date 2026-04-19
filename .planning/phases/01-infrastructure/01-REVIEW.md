---
phase: 01-infrastructure
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - organizer.py
  - test_organizer_t1.py
  - verify_t1.py
  - verify_t2.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-04-19
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The Phase 1 infrastructure skeleton is well-structured. The hard-block safety design (INFRA-03, INFRA-04)
is correctly centralized in `Executor.move` rather than scattered across call sites. The two-stage logging
setup (console first, file after drive selection) is the right pattern for this use case.

Three warnings were found, all in `organizer.py`. None are data-loss or security risks in this phase,
but two of them will cause incorrect runtime behavior (duplicate log output) once the script runs repeatedly
or the logging helpers are called more than once. The third is a variable shadowing issue that does not
cause a bug today but is a latent hazard for Phase 2 when the logger is used more heavily.

---

## Warnings

### WR-01: `setup_console_logging` has no guard against duplicate handlers

**File:** `organizer.py:156-164`
**Issue:** `setup_console_logging()` unconditionally adds a `StreamHandler` to the `"organizer"` logger
every time it is called. Python's `logging.getLogger` returns the same singleton object on every call.
If `setup_console_logging()` is ever called twice (e.g., in tests, or if a future phase re-imports),
the logger accumulates duplicate handlers and every log line is printed multiple times.
Verified: after two calls the logger has 2 handlers and each `logger.info(...)` prints twice.

**Fix:**
```python
def setup_console_logging() -> logging.Logger:
    logger = logging.getLogger("organizer")
    if logger.handlers:          # already configured — skip (idempotent)
        return logger
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger
```

---

### WR-02: `add_file_logging` has no guard against duplicate file handlers

**File:** `organizer.py:167-184`
**Issue:** Same problem as WR-01. `add_file_logging()` adds a `RotatingFileHandler` on every call with
no check for existing handlers. Calling it twice appends a second file handler to the same logger.
In practice, `main()` calls it once, but test/verify scripts that import the module may trigger it
multiple times within the same process. The second handler also opens a second file lock on
`organizer.log`, which causes `PermissionError` when `tempfile.TemporaryDirectory` tries to clean up
on Windows — already observed in the test environment.

**Fix:**
```python
def add_file_logging(logger: logging.Logger, log_dir: Path) -> None:
    # Guard: skip if a RotatingFileHandler for this log_dir is already attached
    log_file = log_dir / "organizer.log"
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and Path(h.baseFilename) == log_file:
            return
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.warning("No se pudo crear el directorio de logs (disco de solo lectura). Usando solo consola.")
        return
    fh = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
```

---

### WR-03: `main()` and `setup_console_logging()` shadow the module-level `logger`

**File:** `organizer.py:158, 243`
**Issue:** The module-level `logger = logging.getLogger("organizer")` at line 39 is used by `Executor.move`
(lines 127, 129, 133, 138, 140, 143). Both `setup_console_logging()` (line 158) and `main()` (line 243)
declare a local variable also named `logger` that refers to the same object. This is not a bug today
because `getLogger("organizer")` always returns the same singleton. However, it creates confusion: a
reader of `setup_console_logging` cannot tell at a glance whether the local `logger` is the module logger
or a different one. In Phase 2, if anyone adds handler configuration to the local and forgets the
module-level one is the live object used by `Executor`, this will cause subtle logging gaps.

**Fix — option A (preferred):** Return and expose the module-level logger directly.
```python
# setup_console_logging: don't rebind to a local, configure the module-level one
def setup_console_logging() -> logging.Logger:
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger

# main: no local logger variable; call setup and ignore or discard the return value
def main() -> None:
    setup_console_logging()
    drive = select_drive(get_removable_drives())
    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)
    executor = Executor(dry_run=False)
    show_menu(executor, drive)
```

---

## Info

### IN-01: `_free_path` has no upper bound on the collision counter

**File:** `organizer.py:108-112`
**Issue:** The `while True` loop in `_free_path` has no maximum iteration limit. If a directory
somehow contains thousands of files named `movie (N).mkv` — or if a filesystem is read-only
and `candidate.exists()` always returns False for non-deterministic reasons — the loop runs
indefinitely. Not a crash risk in normal operation, but worth bounding as a defensive measure.

**Fix:**
```python
MAX_COLLISION_COUNTER = 9999
counter = 2
while counter <= MAX_COLLISION_COUNTER:
    candidate = parent / f"{stem} ({counter}){suffix}"
    if not candidate.exists():
        return candidate
    counter += 1
raise RuntimeError(f"No se pudo encontrar un nombre libre para: {dst} (hasta ({MAX_COLLISION_COUNTER}))")
```

---

### IN-02: `verify_t1.py` and `verify_t2.py` depend on `CWD` being the project root

**File:** `verify_t1.py:2`, `verify_t2.py:2`
**Issue:** Both files use `sys.path.insert(0, '.')` and load `organizer.py` via the relative path
`'organizer.py'`. If either script is run from a different working directory (e.g., `python
.planning/phases/.../verify_t1.py`), the load fails with a `FileNotFoundError` on `organizer.py`
rather than a clear diagnostic. The subprocess in `verify_t2.py` (line 18) has the same fragility
since it references `'organizer.py'` directly.

**Fix:** Use `Path(__file__).parent / "organizer.py"` as `test_organizer_t1.py` already does
correctly (line 14):
```python
# verify_t1.py and verify_t2.py — replace the spec line:
spec = importlib.util.spec_from_file_location(
    'organizer', Path(__file__).parent / 'organizer.py'
)
```

---

### IN-03: `re` module imported but not used in current code

**File:** `organizer.py:8`
**Issue:** `import re` is present in the stdlib imports block but `re` is not referenced anywhere
in the current file. This is a planned forward import (per CLAUDE.md, regex patterns are
needed in Phase 2), which the comment in `SECTION 1` implies. The import is harmless but will
trigger linter warnings (e.g., `F401 're' imported but unused` in flake8/ruff).

**Fix (if linting is enforced):** Add a `# noqa: F401  # used in Phase 2` annotation, or defer
the import until Phase 2 when the patterns are actually defined:
```python
import re  # noqa: F401 — patterns added in Phase 2
```

---

_Reviewed: 2026-04-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

# Phase 3: Safety Features - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 1 file modified (organizer.py) — 7 distinct change units
**Analogs found:** 7 / 7 (all within organizer.py itself)

---

## File Classification

All changes land in `organizer.py`. Each change unit is classified independently.

| Change Unit | Role | Data Flow | Closest Analog (in organizer.py) | Match Quality |
|-------------|------|-----------|----------------------------------|---------------|
| `Executor.__init__` — add accumulator fields | class/model | stateful accumulation | `Executor.__init__` line 142 (existing `dry_run` field) | exact |
| `Executor.move()` — append to `_moves` on success | class method / mutation point | event-driven (per-move side-effect) | `Executor.move()` lines 145–169 (existing move + logger.info) | exact |
| `flush_undo_log(log_path, data)` — atomic write helper | utility | file-I/O | `add_file_logging()` lines 191–209 (writes to `_organizer_logs`, handles PermissionError) | role-match |
| `_prepare_executor_for_run(executor, drive)` — set per-run metadata | utility | transform | `_print_summary(counts)` lines 495–505 (small helper called from menu before/after op) | role-match |
| `_flush_and_clear(executor, log_path)` — post-op flush gate | utility | file-I/O | `_print_summary(counts)` lines 495–505 (same call-site pattern in show_menu) | role-match |
| `undo_last_run(drive, all_drives)` — revert logic | service function | file-I/O + CRUD (reverse) | `apply_renames(executor, drive_root)` lines 254–320 (reads a file, loops entries, calls executor.move, counts results) | exact |
| `show_menu()` + `main()` — wire option 3, add flush calls, signature change | controller / menu loop | request-response | `show_menu()` lines 508–537, `main()` lines 540–549 | exact |

---

## Pattern Assignments

### `Executor.__init__` — accumulator fields (lines 142–143)

**Analog:** `Executor.__init__`, `organizer.py` lines 141–143

**Existing pattern to extend** (lines 141–143):
```python
class Executor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run  # mutable — Phase 2 menu: executor.dry_run = True
```

**New fields to add — copy this exact structure:**
```python
class Executor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run  # mutable — Phase 2 menu: executor.dry_run = True
        self._moves: list[dict] = []       # per-run move accumulator; cleared before each op
        self._log_serial: int = 0          # set by _prepare_executor_for_run
        self._log_drive_root: str = ""     # set by _prepare_executor_for_run
```

**Convention to follow:** All instance fields declared in `__init__`, type-annotated inline using Python 3.9+ syntax (`list[dict]` not `List[dict]`). Comment explains mutation site, not just purpose.

---

### `Executor.move()` — append record after successful real move

**Analog:** `Executor.move()`, `organizer.py` lines 145–169

**Existing success path** (lines 159–168 — the block to extend):
```python
        self.ensure_dir(final_dst.parent)
        try:
            shutil.move(str(src), str(final_dst))  # NOT Path.rename — fails cross-filesystem
            logger.info("MOVE: %s -> %s", src, final_dst)
        except PermissionError:
            logger.error("DENY: %s (acceso denegado)", src)
            return None
        except OSError as exc:
            logger.error("ERR: %s : %s", src, exc)
            return None
        return final_dst
```

**Append pattern — insert after `logger.info("MOVE: ...")`, before `return final_dst`:**
```python
            logger.info("MOVE: %s -> %s", src, final_dst)
            # Accumulate for undo log — only on real moves (dry_run already gated above)
            if self._log_drive_root:
                drive_root = Path(self._log_drive_root)
                try:
                    src_rel = str(src.relative_to(drive_root))
                    dst_rel = str(final_dst.relative_to(drive_root))
                except ValueError:
                    src_rel = str(src)
                    dst_rel = str(final_dst)
                self._moves.append({
                    "src": src_rel,
                    "dst": dst_rel,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                })
```

**Import pattern:** `from datetime import datetime` — add to SECTION 1 imports block alongside existing stdlib imports (lines 3–13). Follow the alphabetical `import X` block style; `from X import Y` goes after bare `import` statements consistent with existing `from logging.handlers import RotatingFileHandler` and `from pathlib import Path` at lines 12–13.

**Error handling pattern:** Wrap `relative_to()` in `try/except ValueError` — mirrors the defensive `.get()` / fallback pattern throughout the file (e.g., `apply_renames` lines 272–273).

---

### `flush_undo_log(log_path, data)` — atomic JSON write utility

**Analog:** `add_file_logging()`, `organizer.py` lines 191–209

**Import/path pattern from analog** (lines 191–209):
```python
def add_file_logging(logger: logging.Logger, log_dir: Path) -> None:
    """Stage 2: call after drive is selected. Adds rotating file handler (INFRA-08)."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.warning("No se pudo crear el directorio de logs (disco de solo lectura). Usando solo consola.")
        return
    log_file = log_dir / "organizer.log"
```

**Key conventions to copy:**
- `Path.mkdir(parents=True, exist_ok=True)` for directory creation
- `try/except PermissionError` + logger.warning + graceful return
- Path constructed via `/` operator: `log_dir / "organizer.log"`

**Core pattern for `flush_undo_log`:**
```python
def flush_undo_log(log_path: Path, data: dict) -> None:
    """Write undo log atomically. No-op if moves list is empty."""
    if not data.get("moves"):
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = log_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(log_path))  # atomic on same filesystem (MoveFileExW)
    except PermissionError:
        logger.warning("No se pudo escribir el log de undo (disco de solo lectura).")
    except OSError as exc:
        logger.error("ERR escribiendo log de undo: %s", exc)
```

**json.dump convention** (from CLAUDE.md): `json.dumps(data, indent=2, ensure_ascii=False)` — exact parameters, no variation.

**os.replace pattern:** `os.replace(str(tmp), str(log_path))` — both args cast to `str()`, same as `shutil.move(str(src), str(final_dst))` on line 161.

---

### `_prepare_executor_for_run(executor, drive)` — per-run setup helper

**Analog:** `_print_summary(counts)`, `organizer.py` lines 495–505

**Existing helper structure to copy** (lines 495–505):
```python
def _print_summary(counts: dict) -> None:
    """MENU-03: one-line operation summary. print() not logger (user-visible output).
    ...
    """
    p = counts.get("procesados", 0)
    ...
    print(f"[OK] Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")
```

**Conventions to copy:**
- Leading underscore = internal helper not called externally
- Docstring on first line explaining requirement reference (MENU-03 style)
- Direct field assignment, no return value

**Core pattern:**
```python
def _prepare_executor_for_run(executor: Executor, drive: dict) -> None:
    """Set per-run metadata on executor and clear move accumulator before each operation."""
    executor._log_serial = drive["serial"]
    executor._log_drive_root = drive["root"]
    executor._moves = []
```

---

### `_flush_and_clear(executor, log_path)` — post-operation flush gate

**Analog:** `_print_summary(counts)`, `organizer.py` lines 495–505 (same call-site pattern in show_menu)

**Call-site pattern from show_menu** (lines 524–529):
```python
        elif choice == "1":
            counts = organize_videos_and_games(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "2":
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
```

**Core pattern — called in the same position as `_print_summary`, after it:**
```python
def _flush_and_clear(executor: Executor, log_path: Path) -> None:
    """Write undo log atomically if this was a real run with recorded moves."""
    if executor.dry_run:
        return  # dry-run: no real moves, nothing to undo
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

**JSON field names** (from CLAUDE.md + D-03 in CONTEXT.md): `serial`, `drive_root`, `timestamp`, `moves` at top level; `src`, `dst`, `ts` per move entry. Do not rename.

---

### `undo_last_run(drive, all_drives)` — revert function

**Analog:** `apply_renames(executor, drive_root)`, `organizer.py` lines 254–320

**Structural pattern from `apply_renames`** — read file, validate, loop entries, call move, count results:

Entry validation pattern (lines 272–278):
```python
        old_str = (row.get("old_path") or "").strip()
        new_str = (row.get("new_path") or "").strip()
        if not old_str or not new_str:
            logger.warning("Fila %d ignorada: faltan columnas old_path / new_path.", i)
            continue
```

Path traversal guard pattern (lines 296–313) — **copy this exact pattern for undo**:
```python
        try:
            src_resolved = src.resolve()
            dst_resolved = dst.resolve()
        except OSError:
            logger.warning("Fila %d ignorada: no se pudo resolver la ruta.", i)
            counts["saltados"] += 1
            continue
        drive_root_str = str(drive_root.resolve()).lower()
        src_str_low = str(src_resolved).lower()
        dst_str_low = str(dst_resolved).lower()
        if not (src_str_low.startswith(drive_root_str + "\\") or src_str_low == drive_root_str) or \
                not (dst_str_low.startswith(drive_root_str + "\\") or dst_str_low == drive_root_str):
            logger.warning(
                "SKIP (path traversal): fila %d — ruta fuera de la unidad seleccionada: src=%s dst=%s",
                i, src_resolved, dst_resolved,
            )
            counts["saltados"] += 1
            continue
```

Move + count pattern (lines 314–318):
```python
        result = executor.move(src, dst)
        if result is not None:
            counts["movidos"] += 1
        else:
            counts["errores"] += 1
```

**Divergence for undo:** Undo does NOT use `executor.move()` — it calls `shutil.move()` directly (moves are not logged again) and uses its own `reverted/skipped/errors` counters. Use `logger.info("UNDO: ...")` and `logger.error("UNDO ERR: ...")` to match the existing `logger.info("MOVE: ...")` / `logger.error("ERR: ...")` convention.

**Summary output pattern** — copy `_print_summary` style (line 505):
```python
print(f"[OK] Revertidos: {reverted} | Saltados: {len(skipped)} | Errores: {errors}")
```
Use `[OK]` ASCII marker (same as `_print_summary` — avoids UnicodeEncodeError on cp1252 terminals).

**JSON read pattern** — use `json.loads(candidate.read_text(encoding="utf-8"))` (matches `tmp.write_text(..., encoding="utf-8")` in flush). Wrap in `try/except (json.JSONDecodeError, OSError)` — same defensive pattern as the `PermissionError` catches throughout.

**Directory creation before revert move** — `src_abs.parent.mkdir(parents=True, exist_ok=True)` mirrors `Executor.ensure_dir()` line 171–175.

**Log deletion after undo** — `actual_log_path.unlink()` wrapped in `try/except OSError: pass` — same silent-skip pattern as `_remove_empty_dirs` lines 381–383:
```python
        try:
            child.rmdir()
            ...
        except OSError:
            pass  # not empty or permission denied — skip silently
```

---

### `show_menu()` + `main()` — wire option 3, add flush calls, signature change

**Analog:** `show_menu()` lines 508–537, `main()` lines 540–549

**Existing option dispatch pattern** (lines 524–529):
```python
        elif choice == "1":
            counts = organize_videos_and_games(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "2":
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
        elif choice == "3":
            print("(Disponible en Fase 3)")
```

**New option 1 and 2 pattern — add prepare + flush calls:**
```python
        elif choice == "1":
            _prepare_executor_for_run(executor, drive)
            counts = organize_videos_and_games(executor, Path(drive["root"]))
            _print_summary(counts)
            _flush_and_clear(executor, log_path)
        elif choice == "2":
            _prepare_executor_for_run(executor, drive)
            counts = apply_renames(executor, Path(drive["root"]))
            _print_summary(counts)
            _flush_and_clear(executor, log_path)
        elif choice == "3":
            undo_last_run(drive, drives)
```

**`log_path` variable** — construct once before the `while True` loop inside `show_menu()`:
```python
    log_path = Path(drive["root"]) / LOG_DIR_NAME / "last_run.json"
```
Follows the same `Path(drive["root"]) / LOG_DIR_NAME` pattern used in `main()` line 545.

**Signature change** (add `drives` parameter — Pitfall 6 from RESEARCH.md):
```python
def show_menu(executor: Executor, drive: dict, drives: list[dict]) -> None:
```

**`main()` update** — pass `drives` at call site:

Existing `main()` pattern (lines 540–549):
```python
def main() -> None:
    """Script entry point. No CLI arguments required (MENU-01)."""
    logger = setup_console_logging()
    drive = select_drive(get_removable_drives())
    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)
    executor = Executor(dry_run=False)
    show_menu(executor, drive)
```

New `main()` — capture `drives` before `select_drive`:
```python
def main() -> None:
    """Script entry point. No CLI arguments required (MENU-01)."""
    logger = setup_console_logging()
    drives = get_removable_drives()
    drive = select_drive(drives)
    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)
    executor = Executor(dry_run=False)
    show_menu(executor, drive, drives)
```

---

## Shared Patterns

### Error handling — PermissionError + OSError two-tier catch
**Source:** `Executor.move()`, `organizer.py` lines 162–168; `add_file_logging()` lines 193–197
**Apply to:** `flush_undo_log()`, `undo_last_run()` revert loop
```python
        except PermissionError:
            logger.error("DENY: %s (acceso denegado)", src)
            return None
        except OSError as exc:
            logger.error("ERR: %s : %s", src, exc)
            return None
```
Always catch `PermissionError` first (it is a subclass of `OSError`), then `OSError` for everything else.

### Path traversal guard
**Source:** `apply_renames()`, `organizer.py` lines 296–313
**Apply to:** `undo_last_run()` per-entry validation
```python
        drive_root_str = str(drive_root.resolve()).lower()
        src_str_low = str(src_resolved).lower()
        if not (src_str_low.startswith(drive_root_str + "\\") or src_str_low == drive_root_str):
            logger.warning("SKIP (path traversal): ...")
            skipped.append(...)
            continue
```
Use `.resolve().lower()` and `startswith(drive_root_str + "\\")` — exact form from `apply_renames`. Do not use `Path.is_relative_to()` (requires Python 3.9+, while `.resolve()` + string prefix works on all 3.x).

### Summary print — [OK] ASCII marker
**Source:** `_print_summary()`, `organizer.py` line 505
**Apply to:** `undo_last_run()` final output
```python
    print(f"[OK] Procesados: {p} | Movidos: {m} | Saltados: {s} | Errores: {e}")
```
`[OK]` not `✓` or `✅` — avoids UnicodeEncodeError on Windows cp1252 console. Fields separated by ` | `.

### Silent skip on OS errors
**Source:** `_remove_empty_dirs()`, `organizer.py` lines 381–383
**Apply to:** `actual_log_path.unlink()` after undo, stale `.tmp` cleanup
```python
        except OSError:
            pass  # not empty or permission denied — skip silently
```

### logger vs print discipline
**Source:** throughout `organizer.py`
**Rule:** `logger.info/warning/error` for file-level events (moves, skips, errors). `print()` for user-visible menu output and summaries. Never swap them. See `_print_summary` docstring line 497: "print() not logger (user-visible output)".

### Section comment convention
**Source:** organizer.py lines 15, 58, 103, 119, 139, 178, 237, 252, 323, 358, 387, 493
**Apply to:** New helper block placement
New functions (`flush_undo_log`, `_prepare_executor_for_run`, `_flush_and_clear`, `undo_last_run`) go in a new `SECTION 15` block inserted between SECTION 14 helpers (`_print_summary`) and the `show_menu` function, OR after `show_menu` before `main()`. Follow `# SECTION N — description` format.

---

## No Analog Found

None — all change units have direct analogs within `organizer.py`.

---

## Metadata

**Analog search scope:** `organizer.py` (single-file project — all analogs are internal)
**Files scanned:** 1 (`organizer.py`, 554 lines)
**Pattern extraction date:** 2026-04-20

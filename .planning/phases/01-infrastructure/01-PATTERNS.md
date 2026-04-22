# Phase 1: Infrastructure - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 1 (single-file architecture: `organizer.py`)
**Analogs found:** 1 / 1 (PowerShell reference — no Python source exists yet)

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `organizer.py` — constants block | config | — | `Ordenar.ps1` lines 8-30 | exact (direct translation) |
| `organizer.py` — drive detection helpers | utility | request-response (OS API) | `Ordenar.ps1` lines 35-56 | role-match (different API: WMI vs ctypes) |
| `organizer.py` — safety helpers | utility | transform | `Ordenar.ps1` lines 58-68 | exact |
| `organizer.py` — `_free_path()` helper | utility | transform | `Ordenar.ps1` lines 76-90 | exact |
| `organizer.py` — `Executor` class | service | CRUD (dry-run gated) | `Ordenar.ps1` move/rename blocks (lines 144-160, 184-191) | role-match (class abstraction is new) |
| `organizer.py` — logging setup | utility | event-driven | `Ordenar.ps1` lines 101-115 (file append pattern) | partial (RotatingFileHandler replaces flat Out-File) |
| `organizer.py` — `select_drive()` UI | utility | request-response | `Ordenar.ps1` lines 35-56 (Get-BestDriveRoot) | role-match (interactive numbered list is new) |
| `organizer.py` — `show_menu()` / `main()` | controller | event-driven | `Ordenar.ps1` overall script flow | partial (menu shell is new; PS1 has no menu) |

---

## Pattern Assignments

### Constants Block

**Analog:** `Ordenar.ps1` lines 8-30
**Translation note:** `$NO_TOUCH_EXTS` array → Python `frozenset`; `$SKIP_PATH_PARTS` array → Python `tuple` of lowercase strings.

**PS1 source — NO_TOUCH_EXTS** (`Ordenar.ps1` lines 16-20):
```powershell
$NO_TOUCH_EXTS = @(
  ".iso",".bin",".cue",".img",".mdf",".nrg",".chd",".cso",".pbp",
  ".gba",".gbc",".gb",".nes",".sfc",".smc",".n64",".z64",".v64",
  ".3ds",".cia",".nds",".gcm",".wbfs",".wad",".xci",".nsp"
)
```

**Python translation (copy this exactly):**
```python
# Ground truth: Ordenar.ps1 $NO_TOUCH_EXTS (full superset — includes .cso, .pbp, .v64
# which are absent from REQUIREMENTS.md INFRA-03; Ordenar.ps1 is authoritative per CONTEXT.md)
NO_TOUCH_EXTS: frozenset[str] = frozenset({
    ".iso", ".bin", ".cue", ".img", ".mdf", ".nrg", ".chd", ".cso", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".n64", ".z64", ".v64",
    ".3ds", ".cia", ".nds", ".gcm", ".wbfs", ".wad", ".xci", ".nsp",
})
```

**PS1 source — SKIP_PATH_PARTS** (`Ordenar.ps1` lines 23-30):
```powershell
$SKIP_PATH_PARTS = @(
  "\System Volume Information\",
  "\$RECYCLE.BIN\",
  "\WindowsApps\",
  "\Program Files\",
  "\Program Files (x86)\",
  "\Amazon Games\"
)
```

**Python translation (copy this exactly):**
```python
# All lowercase — matched with path.lower() for case-insensitive Windows comparison
# Ground truth: Ordenar.ps1 $SKIP_PATH_PARTS
SKIP_PATH_PARTS: tuple[str, ...] = (
    "\\system volume information\\",
    "\\$recycle.bin\\",
    "\\windowsapps\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\amazon games\\",
)

LOG_DIR_NAME = "_organizer_logs"
```

---

### Drive Detection Helpers

**Analog:** `Ordenar.ps1` lines 35-56 (`Get-BestDriveRoot` function)
**Translation note:** PS1 uses `Get-WmiObject Win32_LogicalDisk` (deprecated on Win11). Python uses `ctypes.windll.kernel32` directly — verified live on target machine.

**PS1 source — drive enumeration** (`Ordenar.ps1` lines 38-55):
```powershell
$cands = Get-WmiObject Win32_LogicalDisk |
  Where-Object { $_.DriveType -in 2,3 } |
  ForEach-Object {
    [PSCustomObject]@{
      Root   = ($_.DeviceID + "\")
      SizeGB = [math]::Round(($_.Size/1GB),2)
      FreeGB = [math]::Round(($_.FreeSpace/1GB),2)
      Vol    = $_.VolumeName
    }
  }
```

**Python pattern (copy from RESEARCH.md Pattern 1 — verified live):**
```python
import ctypes

DRIVE_REMOVABLE = 2

def get_removable_drives() -> list[dict]:
    """Return list of dicts: [{root, label, size_gb, serial}]"""
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    drives = []
    for i in range(26):
        if not (bitmask & (1 << i)):
            continue
        letter = chr(ord("A") + i)
        root = letter + ":\\"
        if kernel32.GetDriveTypeW(root) != DRIVE_REMOVABLE:
            continue
        label = _get_volume_label(kernel32, root)
        size_gb = _get_drive_size_gb(kernel32, root)
        serial = _get_volume_serial(kernel32, root)
        drives.append({"root": root, "label": label, "size_gb": size_gb, "serial": serial})
    return drives

def _get_volume_label(kernel32, root: str) -> str:
    buf = ctypes.create_unicode_buffer(261)
    kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0)
    return buf.value or root.rstrip("\\")

def _get_volume_serial(kernel32, root: str) -> int:
    serial = ctypes.c_ulong()
    kernel32.GetVolumeInformationW(root, None, 0, ctypes.byref(serial), None, None, None, 0)
    return serial.value

def _get_drive_size_gb(kernel32, root: str) -> float:
    total = ctypes.c_ulonglong(0)
    kernel32.GetDiskFreeSpaceExW(root, None, ctypes.byref(total), None)
    return round(total.value / 1_073_741_824, 0)
```

**Critical pitfall from RESEARCH.md Pitfall 1:** Never pass `None` for a ctypes output buffer that Windows will write to. Use `ctypes.byref(c_type_instance)` for serial and size. Passing `None` for the volume label string buffer crashes.

---

### Safety Helpers

**Analog:** `Ordenar.ps1` lines 58-68 (`Should-SkipPath`, `Is-NoTouch`)

**PS1 source** (`Ordenar.ps1` lines 58-68):
```powershell
function Should-SkipPath($path) {
  foreach ($p in $SKIP_PATH_PARTS) {
    if ($path -like "*$p*") { return $true }
  }
  return $false
}

function Is-NoTouch($path) {
  $ext = ([System.IO.Path]::GetExtension($path)).ToLower()
  return ($NO_TOUCH_EXTS -contains $ext)
}
```

**Python translation (copy this exactly):**
```python
def is_no_touch(path: str) -> bool:
    """True if file extension is in the ROM/ISO hard-block list."""
    lower = path.lower()
    dot = lower.rfind(".")
    return lower[dot:] in NO_TOUCH_EXTS if dot >= 0 else False

def should_skip_path(path: str) -> bool:
    """True if path contains any protected system folder component."""
    lower = path.lower()
    return any(part in lower for part in SKIP_PATH_PARTS)
```

---

### `_free_path()` Helper

**Analog:** `Ordenar.ps1` lines 76-90 (`Get-FreePath`) and `Renombrar.ps1` lines 20-34 (`Get-FreeName`)

**PS1 source** (`Ordenar.ps1` lines 76-90):
```powershell
function Get-FreePath($destPath) {
  if (-not (Test-Path -LiteralPath $destPath)) { return $destPath }

  $dir  = Split-Path $destPath
  $name = [System.IO.Path]::GetFileNameWithoutExtension($destPath)
  $ext  = [System.IO.Path]::GetExtension($destPath)

  $i = 2
  do {
    $cand = Join-Path $dir ("$name ($i)$ext")
    $i++
  } while (Test-Path -LiteralPath $cand)

  return $cand
}
```

**Python translation (copy this exactly):**
```python
from pathlib import Path

def _free_path(dst: Path) -> Path:
    """Return dst unchanged if it doesn't exist; otherwise dst with (2), (3)... appended to stem."""
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
```

---

### `Executor` Class

**Analog:** `Ordenar.ps1` move blocks (lines 144-160, 184-191) — the try/catch move + log pattern.

**PS1 source — move with error handling** (`Ordenar.ps1` lines 144-160):
```powershell
$final = Get-FreePath $new

try {
  Clear-Readonly $old
  $finalLeaf = Split-Path $final -Leaf
  Rename-Item -LiteralPath $old -NewName $finalLeaf -ErrorAction Stop
  "[OK] RENAME: $old -> $final" | Out-File $LOG_APPLY -Append
}
catch [System.UnauthorizedAccessException] {
  "[DENY] $old (acceso denegado)" | Out-File $LOG_APPLY -Append
}
catch {
  "[ERR] $old : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
}
```

**Python class pattern (copy from RESEARCH.md Pattern 3):**
```python
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("organizer")

class Executor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run  # mutable so Phase 2 menu can toggle without reconstruction

    def move(self, src: Path, dst: Path) -> Path | None:
        """Move src to dst (collision-safe). Returns final path, or None if blocked."""
        src_str = str(src)

        # Hard blocks — enforced at the single mutation point, not at call sites
        if is_no_touch(src_str):
            logger.warning("SKIP (no-touch ext): %s", src)
            return None
        if should_skip_path(src_str):
            logger.warning("SKIP (protected path): %s", src)
            return None

        final_dst = _free_path(dst)

        if self.dry_run:
            logger.info("DRY-RUN MOVE: %s -> %s", src, final_dst)
            return final_dst

        self.ensure_dir(final_dst.parent)
        try:
            shutil.move(str(src), str(final_dst))
            logger.info("MOVE: %s -> %s", src, final_dst)
        except PermissionError:
            logger.error("DENY: %s (acceso denegado)", src)
            return None
        except OSError as exc:
            logger.error("ERR: %s : %s", src, exc)
            return None
        return final_dst

    def ensure_dir(self, path: Path) -> None:
        """Create directory tree. No-op in dry_run mode."""
        if self.dry_run:
            return
        path.mkdir(parents=True, exist_ok=True)
```

**Key design rules:**
- `dry_run` is a mutable attribute — Phase 2 menu can set `executor.dry_run = True/False` without reconstructing.
- Safety guards live inside `move()`, never at call sites.
- Use `shutil.move(str(src), str(final_dst))` — never `Path.rename()` (fails cross-filesystem).
- Catch `PermissionError` and `OSError` separately, matching PS1's two-level catch pattern.

---

### Logging Setup (Dual Output)

**Analog:** `Ordenar.ps1` lines 101-115 (flat `Out-File` append pattern — Python uses RotatingFileHandler instead)

**PS1 source** (`Ordenar.ps1` lines 101-115):
```powershell
$LOG_DIR   = Join-Path $DISK_ROOT "_organizer_logs"
$LOG_APPLY = Join-Path $LOG_DIR "rename_apply_and_organize.log"
Ensure-Dir $LOG_DIR
"==== INICIO $(Get-Date) ====" | Out-File $LOG_APPLY -Encoding UTF8
```

**Python pattern (two-stage — console first, file added after drive selection):**
```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_console_logging() -> logging.Logger:
    """Stage 1: call at startup before drive is known. Console output only."""
    logger = logging.getLogger("organizer")
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger

def add_file_logging(logger: logging.Logger, log_dir: Path) -> None:
    """Stage 2: call after drive selected. Adds rotating file handler."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.warning("No se pudo crear el directorio de logs (disco de solo lectura). Usando solo consola.")
        return
    log_file = log_dir / "organizer.log"
    fh = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,   # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
```

**Log dir convention** (from `Ordenar.ps1` line 103 and CLAUDE.md):
```python
log_dir = Path(drive["root"]) / "_organizer_logs"
```

---

### Drive Selection UI (`select_drive()`)

**Analog:** `Ordenar.ps1` lines 35-56 (`Get-BestDriveRoot`) — but the Python version is fully interactive; the PS1 version silently auto-selects. The numbered-list format is new.

**PS1 source — auto-select logic** (`Ordenar.ps1` lines 35-56):
```powershell
function Get-BestDriveRoot($preferred) {
  if (Test-Path -LiteralPath $preferred) { return $preferred }
  # ... auto-picks largest drive with >= 50 GB free
  if ($cands -and $cands.Count -ge 1) { return $cands[0].Root }
  throw "No encuentro $preferred ni pude autodetectar un disco válido."
}
```

**Python pattern (decisions D-01/D-02/D-03 are locked):**
```python
import sys

def select_drive(drives: list[dict]) -> dict:
    """
    D-02: no drives → print message + exit.
    D-01: one drive → auto-select silently.
    D-03: multiple → numbered interactive list.
    """
    if not drives:
        print("No se encontraron unidades extraíbles. Conecta un disco e inténtalo de nuevo.")
        sys.exit(1)

    if len(drives) == 1:
        d = drives[0]
        print(f"Usando {d['root']} ({d['label']})")
        return d

    print("Unidades extraíbles disponibles:")
    for i, d in enumerate(drives, 1):
        size_str = f"{int(d['size_gb'])} GB"
        print(f"  {i}) {d['root']} {d['label']} ({size_str})")

    while True:
        choice = input(f"Selecciona una unidad [1-{len(drives)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(drives):
            return drives[int(choice) - 1]
        print(f"Entrada inválida. Escribe un número entre 1 y {len(drives)}.")
```

**Display format** (locked by D-03 decision): `1) F:\ MEDIOS (931 GB)` — letter + label + size in GB, no decimals.

---

### Main Menu Loop (`show_menu()` / `main()`)

**Analog:** `Ordenar.ps1` overall script flow (no menu exists — the PS1 runs top-to-bottom once). The numbered `while True` menu is entirely new.

**Python pattern (no PS1 analog — design from CLAUDE.md and RESEARCH.md Pattern 7):**
```python
def show_menu(executor: Executor, drive: dict) -> None:
    while True:
        print()
        print(f"=== Organizador | {drive['root']} {drive['label']} ===")
        print("  1) Organizar vídeos y juegos")
        print("  2) Aplicar rename_plan.tsv")
        print("  3) Revertir última operación")
        print("  4) Detectar incoherencias")
        print("  0) Salir")
        choice = input("Opción: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("(Disponible en Fase 2)")
        elif choice == "2":
            print("(Disponible en Fase 2)")
        elif choice == "3":
            print("(Disponible en Fase 3)")
        elif choice == "4":
            print("(Disponible en Fase 4)")
        else:
            print("Opción inválida.")


def main() -> None:
    logger = setup_console_logging()
    drives = get_removable_drives()
    drive = select_drive(drives)

    log_dir = Path(drive["root"]) / LOG_DIR_NAME
    add_file_logging(logger, log_dir)

    executor = Executor(dry_run=False)
    show_menu(executor, drive)


if __name__ == "__main__":
    main()
```

---

## Shared Patterns

### File Layout (internal order within `organizer.py`)

From RESEARCH.md Architecture Patterns — internal structure (top to bottom):

```python
# 1. stdlib imports only
# 2. Constants (NO_TOUCH_EXTS, SKIP_PATH_PARTS, LOG_DIR_NAME)
# 3. Drive detection helpers (get_removable_drives, _get_volume_label, _get_volume_serial, _get_drive_size_gb)
# 4. Safety helpers (is_no_touch, should_skip_path)
# 5. Path helpers (_free_path)
# 6. Executor class (dry_run, move, ensure_dir)
# 7. Logging setup (setup_console_logging, add_file_logging)
# 8. Drive selection UI (select_drive)
# 9. Main menu + entry point (show_menu, main, if __name__ == "__main__")
```

### Error Handling Pattern

**Source:** `Ordenar.ps1` try/catch blocks (lines 144-160, 184-191, 262-268)
**Apply to:** `Executor.move()` and `add_file_logging()`

Two-level catch — specific exception first, broad `OSError` second:
```python
try:
    shutil.move(str(src), str(final_dst))
    logger.info("MOVE: %s -> %s", src, final_dst)
except PermissionError:
    logger.error("DENY: %s (acceso denegado)", src)
    return None
except OSError as exc:
    logger.error("ERR: %s : %s", src, exc)
    return None
```

### Logging Call Pattern

**Source:** CLAUDE.md + RESEARCH.md Pattern 5
**Apply to:** Every function that performs a skippable or executable action

```python
logger = logging.getLogger("organizer")   # module-level, after imports

# Inside functions:
logger.warning("SKIP (...): %s", path)   # for blocks/skips
logger.info("MOVE: %s -> %s", src, dst)  # for successful ops
logger.error("ERR: %s : %s", path, exc)  # for failures
logger.debug("...")                        # for diagnostic detail
```

Never use `print()` for operational messages — only for the interactive UI (menu, drive selection prompts).

### Path Construction Pattern

**Source:** CLAUDE.md tech stack table
**Apply to:** Every place a path is constructed

```python
from pathlib import Path

# Use / operator, never os.path.join or string concatenation
log_dir = Path(drive["root"]) / "_organizer_logs"
candidate = parent / f"{stem} ({counter}){suffix}"

# Always pass str() to shutil and os functions that don't accept Path natively
shutil.move(str(src), str(dst))
```

### Directory Traversal Pattern

**Source:** RESEARCH.md Standard Stack, INFRA-05 constraint
**Apply to:** Any future file discovery in Phases 2-4 (not Phase 1 itself, but Executor must not violate this)

```python
# ALWAYS use os.scandir with context manager — never glob, never rglob
with os.scandir(directory) as entries:
    for entry in entries:
        if entry.is_dir(follow_symlinks=False):
            # recurse
            pass
        elif entry.is_file(follow_symlinks=False):
            # process
            pass
```

---

## No Analog Found

| Capability | Role | Data Flow | Reason |
|------------|------|-----------|--------|
| Numbered interactive menu shell | controller | event-driven | PS1 scripts have no menu; they run top-to-bottom once |
| Two-stage logging (console-first, file-after-drive) | utility | event-driven | PS1 uses flat `Out-File` append; no handler lifecycle |

For these two capabilities, use RESEARCH.md Patterns 5 and 7 directly — they are fully verified designs.

---

## Metadata

**Analog search scope:** Repository root (`.ps1` files only — no Python source exists)
**Files scanned:** `Ordenar.ps1` (318 lines), `Renombrar.ps1` (67 lines)
**Pattern extraction date:** 2026-04-19
**Ground-truth precedence:** `Ordenar.ps1` > `REQUIREMENTS.md` for `NO_TOUCH_EXTS` and `SKIP_PATH_PARTS` (per CONTEXT.md canonical refs)

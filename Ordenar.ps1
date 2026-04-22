# =========================
# Organizar_Final.ps1
# - Renombra desde rename_plan.tsv (robusto)
# - Reorganiza Series / Peliculas / Juegos (conservador)
# =========================

# --------- Ajustes ----------
$PreferredRoot = "F:\"   # si no existe, autodetecta
$MinFreeGBToConsiderDrive = 50

# extensiones "media" que sí organizamos
$VIDEO_EXTS = @(".mp4",".mkv",".avi",".mov",".m4v",".wmv",".mpg",".mpeg",".ts")
$SUB_EXTS   = @(".srt",".ass",".sub",".idx")

# ROMs / ISOs / imágenes de disco: NO TOCAR (ni renombrar ni mover)
$NO_TOUCH_EXTS = @(
  ".iso",".bin",".cue",".img",".mdf",".nrg",".chd",".cso",".pbp",
  ".gba",".gbc",".gb",".nes",".sfc",".smc",".n64",".z64",".v64",
  ".3ds",".cia",".nds",".gcm",".wbfs",".wad",".xci",".nsp"
)

# carpetas típicamente protegidas o con permisos raros (skip)
$SKIP_PATH_PARTS = @(
  "\System Volume Information\",
  "\$RECYCLE.BIN\",
  "\WindowsApps\",
  "\Program Files\",
  "\Program Files (x86)\",
  "\Amazon Games\"
)

# --------- Helpers ----------
function Has-Cmd($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Get-BestDriveRoot($preferred) {
  if (Test-Path -LiteralPath $preferred) { return $preferred }

  try {
    $cands = Get-WmiObject Win32_LogicalDisk |
      Where-Object { $_.DriveType -in 2,3 } | # removable/fixed
      ForEach-Object {
        [PSCustomObject]@{
          Root   = ($_.DeviceID + "\")
          SizeGB = [math]::Round(($_.Size/1GB),2)
          FreeGB = [math]::Round(($_.FreeSpace/1GB),2)
          Vol    = $_.VolumeName
        }
      } |
      Where-Object { $_.FreeGB -ge $MinFreeGBToConsiderDrive } |
      Sort-Object SizeGB -Descending

    if ($cands -and $cands.Count -ge 1) { return $cands[0].Root }
  } catch {}

  throw "No encuentro $preferred ni pude autodetectar un disco válido."
}

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

function Ensure-Dir($path) {
  if (-not (Test-Path -LiteralPath $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}

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

function Clear-Readonly($path) {
  try {
    $item = Get-Item -LiteralPath $path -ErrorAction Stop
    if ($item.Attributes -band [IO.FileAttributes]::ReadOnly) {
      $item.Attributes = $item.Attributes -bxor [IO.FileAttributes]::ReadOnly
    }
  } catch {}
}

# --------- Root & Logs ----------
$DISK_ROOT = Get-BestDriveRoot $PreferredRoot
$LOG_DIR   = Join-Path $DISK_ROOT "_organizer_logs"
$PLAN_FILE = Join-Path $LOG_DIR "rename_plan.tsv"
$LOG_APPLY = Join-Path $LOG_DIR "rename_apply_and_organize.log"

Ensure-Dir $LOG_DIR

"==== INICIO $(Get-Date) ====" | Out-File $LOG_APPLY -Encoding UTF8
"[INFO] Root: $DISK_ROOT"      | Out-File $LOG_APPLY -Append -Encoding UTF8

if (-not (Test-Path -LiteralPath $PLAN_FILE)) {
  "[ERR] No existe: $PLAN_FILE" | Out-File $LOG_APPLY -Append
  throw "No encuentro rename_plan.tsv en $LOG_DIR"
}

# =========================
# 1) APLICAR RENOMBRADO
# =========================
"[STEP] Aplicando renombrado desde rename_plan.tsv" | Out-File $LOG_APPLY -Append

Import-Csv -LiteralPath $PLAN_FILE -Delimiter "`t" | ForEach-Object {

  $old = $_.old_path
  $new = $_.new_path

  if ([string]::IsNullOrWhiteSpace($old) -or [string]::IsNullOrWhiteSpace($new)) { return }
  if (Should-SkipPath $old) {
    "[SKIP] Protegido: $old" | Out-File $LOG_APPLY -Append
    return
  }
  if (Is-NoTouch $old) {
    "[SKIP] NO-TOUCH (rom/iso): $old" | Out-File $LOG_APPLY -Append
    return
  }

  # Test-Path con LiteralPath (fix comodines [])
  if (-not (Test-Path -LiteralPath $old)) {
    "[SKIP] No existe: $old" | Out-File $LOG_APPLY -Append
    return
  }

  # si destino tiene comodines en el nombre, también usamos -LiteralPath siempre
  $final = Get-FreePath $new

  try {
    Clear-Readonly $old

    # Renombrar manteniendo misma carpeta (Rename-Item solo cambia el nombre)
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
}

# =========================
# 2) REORGANIZAR JUEGOS (conservador)
# Solo mueve carpetas raíz PC/PS1/PS2/PSP/GBA/GBC a F:\Juegos\...
# =========================
"[STEP] Reorganizando Juegos (solo carpetas raíz PC/PS1/PS2/PSP/GBA/GBC)" | Out-File $LOG_APPLY -Append

$JUEGOS_ROOT = Join-Path $DISK_ROOT "Juegos"
Ensure-Dir $JUEGOS_ROOT

$systems = @("PC","PS1","PS2","PSP","GBA","GBC")

foreach ($sys in $systems) {
  $src = Join-Path $DISK_ROOT $sys
  if (Test-Path -LiteralPath $src) {
    $dest = Join-Path $JUEGOS_ROOT $sys
    Ensure-Dir $dest

    # Mueve el contenido, no la carpeta como tal (evita líos si ya existe)
    Get-ChildItem -LiteralPath $src -ErrorAction SilentlyContinue | ForEach-Object {
      $target = Join-Path $dest $_.Name
      $target2 = Get-FreePath $target
      try {
        Move-Item -LiteralPath $_.FullName -Destination $target2 -ErrorAction Stop
        "[OK] MOVE GAME: $($_.FullName) -> $target2" | Out-File $LOG_APPLY -Append
      } catch {
        "[ERR] MOVE GAME: $($_.FullName) : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
      }
    }
  }
}

# =========================
# 3) REORGANIZAR SERIES / PELICULAS
# - solo vídeos + subs
# - NO TOCAR rom/iso
# =========================
"[STEP] Reorganizando Series / Peliculas (videos + subtitulos)" | Out-File $LOG_APPLY -Append

$SERIES_ROOT   = Join-Path $DISK_ROOT "Series"
$PELICULAS_ROOT= Join-Path $DISK_ROOT "Peliculas"
Ensure-Dir $SERIES_ROOT
Ensure-Dir $PELICULAS_ROOT

# Escaneo conservador: no entrar en Juegos ni logs
$excludeDirs = @(
  (Join-Path $DISK_ROOT "_organizer_logs"),
  (Join-Path $DISK_ROOT "_ORIG"),
  (Join-Path $DISK_ROOT "Juegos")
)

function Is-ExcludedDir($fullPath) {
  foreach ($d in $excludeDirs) {
    if ($fullPath -like "$d*") { return $true }
  }
  return $false
}

# recoge vídeos
Get-ChildItem -Path $DISK_ROOT -Recurse -ErrorAction SilentlyContinue |
Where-Object { -not $_.PSIsContainer } |
Where-Object { $VIDEO_EXTS -contains $_.Extension.ToLower() } |
ForEach-Object {

  $file = $_
  $full = $file.FullName

  if (Is-ExcludedDir $full) { return }
  if (Should-SkipPath $full) { return }
  if (Is-NoTouch $full) { return }

  $baseName = $file.BaseName

  # Detectar series por patrón " - Temporada X" (tu formato nuevo)
  if ($baseName -match "^(?<show>.+?)\s-\sTemporada\s(?<season>\d+)\s-\sEpisodio\s(?<ep>\d+).*") {
    $show   = $Matches["show"].Trim()
    $season = [int]$Matches["season"]

    $showDir   = Join-Path $SERIES_ROOT $show
    $seasonDir = Join-Path $showDir ("Temporada " + $season)

    Ensure-Dir $seasonDir

    $destVideo = Join-Path $seasonDir $file.Name
    $destVideo = Get-FreePath $destVideo

    try {
      Move-Item -LiteralPath $full -Destination $destVideo -ErrorAction Stop
      "[OK] MOVE SERIES: $full -> $destVideo" | Out-File $LOG_APPLY -Append
    } catch {
      "[ERR] MOVE SERIES: $full : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
      return
    }

    # mover subs con mismo basename (en origen)
    foreach ($se in $SUB_EXTS) {
      $subPath = Join-Path $file.DirectoryName ($file.BaseName + $se)
      if (Test-Path -LiteralPath $subPath) {
        $destSub = Join-Path $seasonDir ([System.IO.Path]::GetFileName($subPath))
        $destSub = Get-FreePath $destSub
        try {
          Move-Item -LiteralPath $subPath -Destination $destSub -ErrorAction Stop
          "[OK] MOVE SUB: $subPath -> $destSub" | Out-File $LOG_APPLY -Append
        } catch {
          "[ERR] MOVE SUB: $subPath : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
        }
      }
    }

    return
  }

  # Si no es serie, tratamos como película
  $movieFolderName = $baseName.Trim()

  # intenta detectar año y dejar "Titulo (Año)"
  if ($baseName -match "^(?<t>.+?)\s\((?<y>19\d{2}|20\d{2})\).*") {
    $movieFolderName = ($Matches["t"].Trim() + " (" + $Matches["y"] + ")")
  }

  $movieDir = Join-Path $PELICULAS_ROOT $movieFolderName
  Ensure-Dir $movieDir

  $destMovie = Join-Path $movieDir $file.Name
  $destMovie = Get-FreePath $destMovie

  try {
    Move-Item -LiteralPath $full -Destination $destMovie -ErrorAction Stop
    "[OK] MOVE MOVIE: $full -> $destMovie" | Out-File $LOG_APPLY -Append
  } catch {
    "[ERR] MOVE MOVIE: $full : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
    return
  }

  # mover subs con mismo basename (en origen)
  foreach ($se in $SUB_EXTS) {
    $subPath = Join-Path $file.DirectoryName ($file.BaseName + $se)
    if (Test-Path -LiteralPath $subPath) {
      $destSub = Join-Path $movieDir ([System.IO.Path]::GetFileName($subPath))
      $destSub = Get-FreePath $destSub
      try {
        Move-Item -LiteralPath $subPath -Destination $destSub -ErrorAction Stop
        "[OK] MOVE SUB: $subPath -> $destSub" | Out-File $LOG_APPLY -Append
      } catch {
        "[ERR] MOVE SUB: $subPath : $($_.Exception.Message)" | Out-File $LOG_APPLY -Append
      }
    }
  }
}

"==== FIN $(Get-Date) ====" | Out-File $LOG_APPLY -Append -Encoding UTF8

Write-Host ""
Write-Host "[INFO] Terminado ✅"
Write-Host "[INFO] Log:"
Write-Host "       $LOG_APPLY"

# =========================
# CONFIG
# =========================
$DISK_ROOT = "E:\"
$LOG_DIR   = Join-Path $DISK_ROOT "_organizer_logs"
$PLAN_FILE = Join-Path $LOG_DIR "rename_plan.tsv"
$LOG_APPLY = Join-Path $LOG_DIR "rename_applied.log"

if (-not (Test-Path $PLAN_FILE)) {
    throw "No encuentro rename_plan.tsv en $LOG_DIR"
}

Write-Host "[INFO] Aplicando renombrados desde:"
Write-Host "       $PLAN_FILE"
Write-Host ""

# =========================
# FUNCIONES
# =========================
function Get-FreeName($path) {
    if (-not (Test-Path $path)) { return $path }

    $dir  = Split-Path $path
    $name = [System.IO.Path]::GetFileNameWithoutExtension($path)
    $ext  = [System.IO.Path]::GetExtension($path)

    $i = 2
    do {
        $candidate = Join-Path $dir ("$name ($i)$ext")
        $i++
    } while (Test-Path $candidate)

    return $candidate
}

# =========================
# EJECUCIÓN
# =========================
"==== RENOMBRADO INICIADO $(Get-Date) ====" | Out-File $LOG_APPLY -Encoding UTF8

Import-Csv $PLAN_FILE -Delimiter "`t" | ForEach-Object {

    $old = $_.old_path
    $new = $_.new_path

    if (-not (Test-Path $old)) {
        "[SKIP] No existe: $old" | Out-File $LOG_APPLY -Append
        return
    }

    $final = Get-FreeName $new

    try {
        Rename-Item -Path $old -NewName (Split-Path $final -Leaf)
        "[OK] $old -> $final" | Out-File $LOG_APPLY -Append
    } catch {
        "[ERR] $old : $_" | Out-File $LOG_APPLY -Append
    }
}

"==== RENOMBRADO FINALIZADO $(Get-Date) ====" | Out-File $LOG_APPLY -Append

Write-Host ""
Write-Host "[INFO] Renombrado completado ✅"
Write-Host "[INFO] Log:"
Write-Host "       $LOG_APPLY"

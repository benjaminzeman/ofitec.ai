<#!
.SYNOPSIS
  Realiza un respaldo local rápido de los activos críticos del proyecto (DB + código).
.DESCRIPTION
  Crea un directorio con timestamp dentro de backups/ y copia:
    - Bases de datos SQLite en data/ (*.db)
    - Opcional: Zip de carpetas backend/ y frontend/ (parámetro -IncludeCode)
  Mantiene sólo los últimos N respaldos (parámetro -Keep, default 7).
.PARAMETER IncludeCode
  Incluye un zip del código fuente backend + frontend.
.PARAMETER Keep
  Número de respaldos a conservar. Antiguos se eliminan.
.EXAMPLE
  pwsh scripts/backup_local.ps1 -IncludeCode -Keep 10
#>
param(
  [switch]$IncludeCode,
  [int]$Keep = 7
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path $root
Set-Location $repoRoot

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = Join-Path $repoRoot 'backups'
$newBackupDir = Join-Path $backupRoot $timestamp

Write-Host "[backup] Creando carpeta: $newBackupDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $newBackupDir -Force | Out-Null

# 1. Copiar bases de datos
if (Test-Path 'data') {
  $dbFiles = Get-ChildItem -Path 'data' -Filter '*.db' -File -ErrorAction SilentlyContinue
  if ($dbFiles.Count -gt 0) {
    $dbDir = Join-Path $newBackupDir 'data'
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
    foreach ($f in $dbFiles) {
      Copy-Item $f.FullName -Destination (Join-Path $dbDir $f.Name)
      Write-Host "[backup] Copiado DB: $($f.Name)" -ForegroundColor Green
    }
  } else {
    Write-Host "[backup] No se encontraron archivos .db en data/" -ForegroundColor Yellow
  }
} else {
  Write-Host "[backup] Carpeta data/ no existe" -ForegroundColor Yellow
}

# 2. Opcional: Zip de código
if ($IncludeCode) {
  $zipPath = Join-Path $newBackupDir 'codigo.zip'
  Write-Host "[backup] Generando zip de backend/ y frontend/ -> $zipPath" -ForegroundColor Cyan
  $items = @()
  if (Test-Path 'backend') { $items += 'backend' }
  if (Test-Path 'frontend') { $items += 'frontend' }
  if ($items.Count -eq 0) {
    Write-Host '[backup] No hay carpetas backend/ o frontend/ para comprimir' -ForegroundColor Yellow
  } else {
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path $items -DestinationPath $zipPath -Force
    Write-Host "[backup] Zip generado" -ForegroundColor Green
  }
}

# 3. Rotación
if (-not (Test-Path $backupRoot)) { return }
$existing = Get-ChildItem $backupRoot -Directory | Sort-Object Name -Descending
if ($existing.Count -gt $Keep) {
  $toDelete = $existing | Select-Object -Skip $Keep
  foreach ($d in $toDelete) {
    Write-Host "[backup] Eliminando respaldo antiguo: $($d.Name)" -ForegroundColor DarkYellow
    Remove-Item $d.FullName -Recurse -Force
  }
}

Write-Host "[backup] Listo. Últimos respaldos:" -ForegroundColor Cyan
Get-ChildItem $backupRoot -Directory | Sort-Object Name -Descending | Select-Object -First 10 | ForEach-Object { Write-Host " - $($_.Name)" }

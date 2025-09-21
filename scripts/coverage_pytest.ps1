param(
    [string]$DbPath = 'data/chipax_data.db',
    [switch]$Html
)

Write-Host '== Pytest Coverage Report ==' -ForegroundColor Cyan
if (-not (Test-Path $DbPath)) {
  Write-Host "[warn] DB path $DbPath no existe; se creará on-demand si tests la inicializan" -ForegroundColor Yellow
}

$cmd = 'python -m pytest --maxfail=1 --disable-warnings --cov=backend --cov-report=term'
if ($Html) { $cmd += ' --cov-report=html' }

Write-Host "Ejecutando: $cmd" -ForegroundColor DarkGray
Invoke-Expression $cmd

if ($LASTEXITCODE -ne 0) {
  Write-Host 'Tests fallidos.' -ForegroundColor Red
  exit $LASTEXITCODE
}

Write-Host 'Coverage OK.' -ForegroundColor Green
if ($Html) {
  Write-Host 'Abrir ./htmlcov/index.html para reporte detallado.' -ForegroundColor Green
}

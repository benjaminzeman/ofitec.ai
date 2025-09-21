param(
    [switch]$Stress,
    [switch]$Perf,
    [string]$Marker,
    [switch]$SkipStress,
    [switch]$SkipPerf
)

# Helper to run pytest with appropriate marker expression.
$env:PYTHONUNBUFFERED='1'

if ($SkipStress) { $env:SKIP_STRESS_TESTS='1' }
if ($SkipPerf) { $env:SKIP_PERF_TESTS='1' }

$expr = ''
if ($Marker) {
  $expr = $Marker
} elseif ($Stress -and $Perf) {
  $expr = 'stress or perf'
} elseif ($Stress) {
  $expr = 'stress'
} elseif ($Perf) {
  $expr = 'perf'
}

if ($expr) {
  Write-Host "Running pytest with marker expression: $expr" -ForegroundColor Cyan
  C:/Python313/python.exe -m pytest -m "$expr" -q
} else {
  Write-Host "Running full test suite" -ForegroundColor Cyan
  C:/Python313/python.exe -m pytest -q
}

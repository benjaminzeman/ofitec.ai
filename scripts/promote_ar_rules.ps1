param(
    [string]$DbPath = "$PSScriptRoot/../data/chipax_data.db",
    [int]$MinCount = 3,
    [switch]$DryRun
)

# Resolve DB path and ensure it exists
$DbFull = Resolve-Path -Path $DbPath -ErrorAction SilentlyContinue
if (-not $DbFull) {
    Write-Host "Database not found at $DbPath" -ForegroundColor Yellow
}

$env:DB_PATH = if ($DbFull) { $DbFull.Path } else { $DbPath }
$python = "python"
$script = "$PSScriptRoot/../tools/promote_ar_rules.py"

$argList = @($script, "--min-count", $MinCount)
if ($DryRun) { $argList += "--dry-run" }

Write-Host "Running promote_ar_rules..." -ForegroundColor Cyan
& $python @argList
if ($LASTEXITCODE -ne 0) {
    Write-Error "promote_ar_rules failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

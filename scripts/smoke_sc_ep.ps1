# PS script: smoke test Subcontractor EP endpoints
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$base = 'http://127.0.0.1:5555'

function Wait-BackendReady {
  param(
    [int]$TimeoutSec = 60
  )
  $start = Get-Date
  while ((Get-Date) - $start -lt ([TimeSpan]::FromSeconds($TimeoutSec))) {
    try {
      $r = Invoke-RestMethod -Method Get -Uri ($base + '/api/admin/routes') -TimeoutSec 5
      if ($r) { return $true }
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  return $false
}

Write-Host '== Waiting backend ready...'
if (-not (Wait-BackendReady -TimeoutSec 90)) { throw 'Backend not ready on /api/admin/routes' }

try {
  $ping = Invoke-RestMethod -Method Get -Uri ($base + '/api/sc/ping') -TimeoutSec 5
  Write-Host '== SC ping:' ($ping | ConvertTo-Json -Depth 4)
} catch {
  Write-Warning 'SC ping not available yet; continuing with EP creation.'
}

Write-Host '== Create SC EP header'
$header = @{ project_id = 2306; ep_number = 'SC-001'; period_start = '2025-08-01'; period_end = '2025-08-31'; retention_pct = 0.05 } | ConvertTo-Json
$resp = Invoke-RestMethod -Method Post -Uri ($base + '/api/sc/ep') -ContentType 'application/json' -Body $header
$ep = $resp.ep_id
if (-not $ep) { throw 'Failed to create SC EP header' }
Write-Host ('ep_id=' + $ep)

Write-Host '== Set lines'
$lines = @{ lines = @(@{ item_code='P1'; description='Excavation'; unit='m3'; qty_period=10; unit_price=100000; qty_cum=10; amount_cum=1000000 }) } | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri ($base + "/api/sc/ep/$ep/lines/bulk") -ContentType 'application/json' -Body $lines | Out-Null

Write-Host '== Set deductions'
$ded = @{ deductions = @(@{ type='advance_amortization'; description='Advance amortization'; amount=200000 }) } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri ($base + "/api/sc/ep/$ep/deductions/bulk") -ContentType 'application/json' -Body $ded | Out-Null

Write-Host '== Get summary'
$summary = Invoke-RestMethod -Method Get -Uri ($base + "/api/sc/ep/$ep/summary")
$summary | ConvertTo-Json -Depth 6 | Write-Output

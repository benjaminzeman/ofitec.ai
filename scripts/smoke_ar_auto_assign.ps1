# Smoke test for AR auto-assign
param(
    [string]$ServerHost = '127.0.0.1',
    [int]$Port = 5555,
    [string]$CustomerName = 'Cliente XYZ',
    [string]$InvoiceNumber = 'F-TEST-001',
    [int]$TotalAmount = 50000,
    [string]$IssueDate = '2025-08-10',
    [string]$ProjectHint = '2306',
    [double]$Threshold = 0.95,
    [switch]$DryRun
)

Write-Host "== AR Auto-assign smoke" -ForegroundColor Cyan
$baseUrl = "http://${ServerHost}:$Port"
$url = "$baseUrl/api/ar-map/auto_assign"

$payload = @{
    invoice = @{
        customer_name = $CustomerName
        invoice_number = $InvoiceNumber
        total_amount  = $TotalAmount
        issue_date    = $IssueDate
    }
    project_hint = $ProjectHint
    threshold = $Threshold
    dry_run = [bool]$DryRun
}

try {
    $json = $payload | ConvertTo-Json -Depth 6
    Write-Host "POST $url" -ForegroundColor DarkCyan
    $resp = Invoke-RestMethod -Method Post -Uri $url -ContentType 'application/json' -Body $json
    $resp | ConvertTo-Json -Depth 6
} catch {
    Write-Host "Error calling $url" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}

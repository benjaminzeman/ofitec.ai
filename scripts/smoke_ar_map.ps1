# Smoke test for AR map suggestions
param(
    [string]$ServerHost = '127.0.0.1',
    [int]$Port = 5555,
    [string]$CustomerName = 'Z ESTUDIO SPA',
    [string]$CustomerRUT = '77978421-5',
    [int]$TotalAmount = 9815287,
    [string]$IssueDate = '2024-12-30'
)

Write-Host "== AR Map suggestions smoke" -ForegroundColor Cyan
$baseUrl = "http://${ServerHost}:$Port"
$url = "$baseUrl/api/ar-map/suggestions"

$payload = @{
    invoice = @{
        customer_name = $CustomerName
        customer_rut  = $CustomerRUT
        total_amount  = $TotalAmount
        issue_date    = $IssueDate
    }
}

try {
    $json = $payload | ConvertTo-Json -Depth 6
    Write-Host "POST $url" -ForegroundColor DarkCyan
    $resp = Invoke-RestMethod -Method Post -Uri $url -ContentType 'application/json' -Body $json
    $items = @()
    if ($resp -and $resp.items) { $items = $resp.items }
    Write-Host "Suggestions count: $($items.Count)" -ForegroundColor Green
    $resp | ConvertTo-Json -Depth 6
} catch {
    Write-Host "Error calling $url" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}

# Database Cleanup Script for OFITEC.AI
# Automated cleanup of test databases to maintain repository cleanliness

param(
    [string]$DataDir = "data",
    [int]$MaxAgeHours = 24,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Stats
)

function Show-DatabaseStats {
    param([string]$DataPath)
    
    Write-Host "`n📊 DATABASE STATISTICS:" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor Gray
    
    if (-not (Test-Path $DataPath)) {
        Write-Host "❌ Data directory '$DataPath' does not exist" -ForegroundColor Red
        return
    }
    
    $stats = @{}
    $totalSize = 0
    
    Get-ChildItem -Path $DataPath -Filter "*.db" | ForEach-Object {
        $fileSize = $_.Length
        $totalSize += $fileSize
        
        if ($_.Name -like "test_*") {
            $dbType = "test_" + $_.Name.Split('_')[1]
        }
        elseif ($_.Name -like "tmp_*") {
            $dbType = "temporary"
        }
        else {
            $dbType = "production"
        }
        
        if (-not $stats.ContainsKey($dbType)) {
            $stats[$dbType] = @{ Count = 0; Size = 0 }
        }
        
        $stats[$dbType].Count++
        $stats[$dbType].Size += $fileSize
    }
    
    # Display stats
    $stats.GetEnumerator() | Sort-Object Name | ForEach-Object {
        $sizeMB = [math]::Round($_.Value.Size / 1MB, 2)
        $name = $_.Key.PadRight(20)
        $count = $_.Value.Count.ToString().PadLeft(4)
        Write-Host "$name : $count files ($sizeMB MB)"
    }
    
    Write-Host ("-" * 50) -ForegroundColor Gray
    $totalMB = [math]::Round($totalSize / 1MB, 2)
    $totalCount = ($stats.Values | Measure-Object -Property Count -Sum).Sum
    $totalStr = "TOTAL".PadRight(20)
    Write-Host "$totalStr : $($totalCount.ToString().PadLeft(4)) files ($totalMB MB)"
    
    # Show production databases
    Write-Host "`n📁 PRODUCTION DATABASES:" -ForegroundColor Green
    Get-ChildItem -Path $DataPath -Filter "*.db" | 
        Where-Object { -not ($_.Name -like "test_*" -or $_.Name -like "tmp_*") } |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object {
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            $modTime = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
            $name = $_.Name.PadRight(20)
            Write-Host "  $name - $($sizeMB.ToString().PadLeft(6)) MB - $modTime"
        }
}

function Remove-TestDatabases {
    param(
        [string]$DataPath,
        [int]$MaxAge,
        [bool]$IsDryRun
    )
    
    if (-not (Test-Path $DataPath)) {
        Write-Host "❌ Data directory '$DataPath' does not exist" -ForegroundColor Red
        return 0
    }
    
    $cutoffTime = (Get-Date).AddHours(-$MaxAge)
    $cleanedCount = 0
    $totalSize = 0
    
    Write-Host "🔍 Scanning for test databases older than $MaxAge hours..." -ForegroundColor Yellow
    
    $patterns = @("test_*.db", "tmp_*.db")
    
    foreach ($pattern in $patterns) {
        Get-ChildItem -Path $DataPath -Filter $pattern | ForEach-Object {
            try {
                if ($_.LastWriteTime -lt $cutoffTime) {
                    $fileSize = $_.Length
                    $totalSize += $fileSize
                    $ageHours = [math]::Round(((Get-Date) - $_.LastWriteTime).TotalHours, 1)
                    
                    if ($IsDryRun) {
                        Write-Host "[DRY RUN] Would remove: $($_.Name) ($($fileSize.ToString('N0')) bytes, ${ageHours}h old)" -ForegroundColor Magenta
                    }
                    else {
                        Remove-Item $_.FullName -Force
                        Write-Host "✅ Removed: $($_.Name) ($($fileSize.ToString('N0')) bytes, ${ageHours}h old)" -ForegroundColor Green
                    }
                    
                    $cleanedCount++
                }
            }
            catch {
                Write-Host "⚠️  Error processing $($_.Name): $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
    
    if ($cleanedCount -gt 0) {
        $sizeMB = [math]::Round($totalSize / 1MB, 2)
        $action = if ($IsDryRun) { "Would free" } else { "Freed" }
        Write-Host "🧹 $action $sizeMB MB by cleaning $cleanedCount test databases" -ForegroundColor Cyan
    }
    else {
        Write-Host "✨ No old test databases found to clean" -ForegroundColor Green
    }
    
    return $cleanedCount
}

# Main execution
Write-Host "🗄️  OFITEC.AI Database Cleanup Tool" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Gray

# Show stats if requested
if ($Stats) {
    Show-DatabaseStats -DataPath $DataDir
}

# Perform cleanup
$maxAge = if ($Force) { 0 } else { $MaxAgeHours }
$cleaned = Remove-TestDatabases -DataPath $DataDir -MaxAge $maxAge -IsDryRun $DryRun

# Show final stats if any cleaning was done
if ($cleaned -gt 0 -and -not $DryRun) {
    Show-DatabaseStats -DataPath $DataDir
}

Write-Host "`n🎯 Cleanup completed!" -ForegroundColor Green
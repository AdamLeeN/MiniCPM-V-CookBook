#Requires -Version 5.1
<#
.SYNOPSIS
    停止 Windows 上运行的 LiveKit 服务器

.EXAMPLE
    .\stop-livekit-windows.ps1
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Stopping Windows LiveKit" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$Processes = Get-Process | Where-Object { $_.ProcessName -like "*livekit*" }

if (-not $Processes) {
    Write-Host "⚠️  No LiveKit process found" -ForegroundColor Yellow
    exit 0
}

$Killed = 0
foreach ($proc in $Processes) {
    Write-Host "  Stopping LiveKit (PID: $($proc.Id))..." -ForegroundColor Gray
    Stop-Process -Id $proc.Id -Force
    $Killed++
}

Start-Sleep -Seconds 1

# 验证
$Remaining = Get-Process | Where-Object { $_.ProcessName -like "*livekit*" }
if (-not $Remaining) {
    Write-Host ""
    Write-Host "✅ LiveKit stopped ($Killed process(es))" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  Some LiveKit processes could not be stopped" -ForegroundColor Yellow
    $Remaining | ForEach-Object { Write-Host "   PID $($_.Id) still running" -ForegroundColor Yellow }
}

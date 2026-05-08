#Requires -Version 5.1
# 在 Windows 上启动 LiveKit 服务器（供 WSL2 后端使用）
# 前置条件：
#   1. WSL2 启用 mirrored 模式 (.wslconfig -> networkingMode=mirrored)
#   2. livekit-server.exe 放在当前目录
# 用法: .\start-livekit-windows.ps1

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LivekitExe = Join-Path $ProjectDir "livekit-server.exe"
$LivekitConfig = Join-Path $ProjectDir "livekit-windows.yaml"
$LogFile = Join-Path $ProjectDir ".logs" "livekit-windows.log"

# 检查 livekit-server.exe
if (-not (Test-Path $LivekitExe)) {
    Write-Host "livekit-server.exe not found" -ForegroundColor Red
    exit 1
}

# 检查配置文件
if (-not (Test-Path $LivekitConfig)) {
    Write-Host "livekit-windows.yaml not found" -ForegroundColor Red
    exit 1
}

# 确保日志目录存在
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# 检查是否已有 LiveKit 在运行
$Existing = Get-Process | Where-Object { $_.ProcessName -like "*livekit*" }
if ($Existing) {
    Write-Host "LiveKit already running (PID: $($Existing.Id))" -ForegroundColor Yellow
    exit 0
}

Write-Host "Starting LiveKit on Windows..." -ForegroundColor Cyan

# 启动 LiveKit
$Process = Start-Process `
    -FilePath $LivekitExe `
    -ArgumentList "--config", $LivekitConfig `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $LogFile `
    -PassThru

Start-Sleep -Seconds 3

# 验证
$client = New-Object System.Net.Sockets.TcpClient
try {
    $client.Connect("127.0.0.1", 7880)
    $client.Close()
    Write-Host "LiveKit started! PID: $($Process.Id)" -ForegroundColor Green
    Write-Host "  ws://127.0.0.1:7880" -ForegroundColor Green
} catch {
    Write-Host "LiveKit failed to start" -ForegroundColor Red
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

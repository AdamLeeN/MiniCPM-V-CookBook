#Requires -Version 5.1
<#
.SYNOPSIS
    MiniCPM-o one-click deployment script (Windows native, no WSL)
.DESCRIPTION
    Includes Docker services + C++ inference service.
    Run in PowerShell: .\deploy_all_win.ps1
    Or:                powershell -ExecutionPolicy Bypass -File deploy_all_win.ps1
.EXAMPLE
    .\deploy_all_win.ps1
    .\deploy_all_win.ps1 -Mode duplex -Port 9060
    .\deploy_all_win.ps1 -CppDir "C:\path\to\llama.cpp-omni" -ModelDir "C:\path\to\gguf"
#>

param(
    [ValidateSet("simplex", "duplex")]
    [string]$Mode = "simplex",

    [int]$Port = 9260,

    [string]$CppDir = "",
    [string]$ModelDir = "",
    [string]$PythonBin = "",
    [string]$ServerScript = "",
    [string]$RefAudio = ""
)

# ============================================================
# Script directory (auto-detect)
# ============================================================
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# ============================================================
# Required paths - modify according to your environment
# ============================================================

# llama.cpp-omni build root directory (containing build\bin\Release\llama-server.exe)
if (-not $CppDir) { $CppDir = Join-Path $SCRIPT_DIR "..\llama.cpp-omni" }

# GGUF model directory
if (-not $ModelDir) { $ModelDir = Join-Path $SCRIPT_DIR "..\gguf" }

# Python interpreter (auto-detect)
if (-not $PythonBin) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PythonBin = $cmd.Source }
    else {
        $cmd = Get-Command python3 -ErrorAction SilentlyContinue
        if ($cmd) { $PythonBin = $cmd.Source }
    }
}

# ============================================================
# Optional config
# ============================================================
if (-not $ServerScript) { $ServerScript = Join-Path $SCRIPT_DIR "cpp_server\minicpmo_cpp_http_server.py" }
if (-not $RefAudio)     { $RefAudio = Join-Path $SCRIPT_DIR "cpp_server\assets\default_ref_audio.wav" }

$CPP_SERVER_LOG     = Join-Path $env:TEMP "cpp_server.log"
$CPP_SERVER_ERR_LOG = Join-Path $env:TEMP "cpp_server_err.log"

# ============================================================
# Helper functions
# ============================================================
function Write-Step  { param([string]$s, [string]$m) Write-Host "[$s] $m" -ForegroundColor Yellow }
function Write-OK    { param([string]$m) Write-Host "   OK $m" -ForegroundColor Green }
function Write-Err   { param([string]$m) Write-Host "   ERROR $m" -ForegroundColor Red }
function Write-Warn  { param([string]$m) Write-Host "   WARN $m" -ForegroundColor DarkYellow }

# ============================================================
# Path validation
# ============================================================
$hasError = $false

# Check CPP_DIR
if (-not (Test-Path $CppDir -PathType Container)) {
    Write-Err "CPP_DIR does not exist: $CppDir"
    $hasError = $true
} else {
    $CppDir = (Resolve-Path $CppDir).Path
    $llamaServerExe = Join-Path $CppDir "build\bin\Release\llama-server.exe"
    if (-not (Test-Path $llamaServerExe)) {
        Write-Err "llama-server.exe not found: $llamaServerExe"
        Write-Host "   Please compile llama.cpp-omni first:"
        Write-Host "     cd $CppDir"
        Write-Host "     cmake -B build -DLLAMA_BUILD_SERVER=ON -DBUILD_SHARED_LIBS=ON"
        Write-Host "     cmake --build build --config Release -j12"
        $hasError = $true
    }
}

# Check MODEL_DIR
if (-not (Test-Path $ModelDir -PathType Container)) {
    Write-Err "MODEL_DIR does not exist: $ModelDir"
    $hasError = $true
} else {
    $ModelDir = (Resolve-Path $ModelDir).Path
}

# Check PYTHON_BIN
if (-not $PythonBin) {
    Write-Err "Python interpreter not found. Use -PythonBin to specify."
    $hasError = $true
} elseif (-not (Test-Path $PythonBin)) {
    Write-Err "Python interpreter not found: $PythonBin"
    $hasError = $true
}

# Check server script
if (-not (Test-Path $ServerScript)) {
    Write-Err "Python server script not found: $ServerScript"
    $hasError = $true
}

# Check reference audio (non-fatal)
if (-not (Test-Path $RefAudio)) {
    Write-Warn "Reference audio not found: $RefAudio (will use default if available)"
}

if ($hasError) {
    Write-Host "`nUse -? or --help for parameter info." -ForegroundColor Yellow
    exit 1
}

# ============================================================
# Display config
# ============================================================
Write-Host "========================================" -ForegroundColor Blue
Write-Host "   MiniCPM-o Deployment (Windows)      " -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Get local IP (pick the adapter with a default gateway)
$LOCAL_IP = "127.0.0.1"
$netCfg = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
          Where-Object { $null -ne $_.IPv4DefaultGateway } |
          Select-Object -First 1
if ($netCfg -and $netCfg.IPv4Address) {
    $LOCAL_IP = $netCfg.IPv4Address.IPAddress
}

Write-Host "   Local IP :  $LOCAL_IP"   -ForegroundColor Green
Write-Host "   Mode     :  $Mode"       -ForegroundColor Green
Write-Host "   Port     :  $Port"       -ForegroundColor Green
Write-Host "   CPP_DIR  :  $CppDir"     -ForegroundColor Green
Write-Host "   MODEL_DIR:  $ModelDir"   -ForegroundColor Green
Write-Host ""

# ==========================================================
# [1/7] Check Docker
# ==========================================================
Write-Step "1/7" "Checking Docker..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "Docker not installed! Please install Docker Desktop"
    Write-Host "   https://www.docker.com/products/docker-desktop"
    exit 1
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker not running! Please start Docker Desktop"
    exit 1
}
Write-OK "Docker is ready"

# ==========================================================
# [2/7] Update LiveKit Config
# ==========================================================
Write-Step "2/7" "Updating LiveKit config..."

$LIVEKIT_CONFIG = Join-Path $SCRIPT_DIR "omini_backend_code\config\livekit.yaml"
if (Test-Path $LIVEKIT_CONFIG) {
    $content = Get-Content $LIVEKIT_CONFIG -Raw -Encoding UTF8
    $content = $content -replace 'node_ip: .*',  "node_ip: `"$LOCAL_IP`""
    $content = $content -replace 'domain: .*',   "domain: `"$LOCAL_IP`""
    [System.IO.File]::WriteAllText($LIVEKIT_CONFIG, $content)
    Write-OK "LiveKit config updated (IP: $LOCAL_IP)"
} else {
    Write-Err "LiveKit config not found: $LIVEKIT_CONFIG"
    exit 1
}

# ==========================================================
# [3/7] Load Docker Images
# ==========================================================
Write-Step "3/7" "Loading Docker images..."

Push-Location $SCRIPT_DIR

$frontendTar = Join-Path $SCRIPT_DIR "o45-frontend.tar"
if (Test-Path $frontendTar) {
    Write-Host "   Loading frontend image..."
    docker load -i $frontendTar
    Write-OK "Frontend image loaded"
} else {
    Write-Warn "Frontend image not found: $frontendTar"
}

$backendTar = Join-Path $SCRIPT_DIR "omini_backend_code\omni_backend.tar"
if (Test-Path $backendTar) {
    Write-Host "   Loading backend image..."
    docker load -i $backendTar
    Write-OK "Backend image loaded"
} else {
    Write-Warn "Backend image not found: $backendTar"
}

# ==========================================================
# [4/7] Start Docker Services
# ==========================================================
Write-Step "4/7" "Starting Docker services..."

# Stop old services
docker compose down 2>$null | Out-Null

# Start new services
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Err "docker compose up failed"
    Pop-Location; exit 1
}

Write-Host "   Waiting for services to start..."
Start-Sleep -Seconds 10

# Check status
$psOut = docker compose ps 2>&1 | Out-String
if ($psOut -match "Up|running") {
    Write-OK "Docker services started"
    docker compose ps
} else {
    Write-Err "Docker services failed to start"
    docker compose logs
    Pop-Location; exit 1
}

Pop-Location

# ==========================================================
# [5/7] Install Python Dependencies
# ==========================================================
Write-Step "5/7" "Checking Python dependencies..."

$REQUIREMENTS = Join-Path $SCRIPT_DIR "cpp_server\requirements.txt"
if (Test-Path $REQUIREMENTS) {
    Write-Host "   Installing Python dependencies..."
    & $PythonBin -m pip install -q -r $REQUIREMENTS 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some dependencies may not be installed. Run: pip install -r $REQUIREMENTS"
    }
}
Write-OK "Python environment ready"

# ==========================================================
# [6/7] Start C++ Inference Service
# ==========================================================
Write-Step "6/7" "Starting C++ inference service..."

# Stop existing service by command line match (kill entire process tree with taskkill /T)
$oldProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*minicpmo_cpp_http_server*" -or $_.CommandLine -like "*llama-server*" }
foreach ($p in $oldProcs) {
    Write-Host "   Killing process tree PID=$($p.ProcessId) ..."
    # taskkill /T kills the entire process tree (parent + all children)
    & taskkill /T /F /PID $p.ProcessId 2>$null
}

# Also kill any process occupying our ports (only LISTEN/ESTABLISHED, not TIME_WAIT)
$portsToFree = @($Port, ($Port + 1), ($Port + 10000))
foreach ($targetPort in $portsToFree) {
    $conns = Get-NetTCPConnection -LocalPort $targetPort -ErrorAction SilentlyContinue |
             Where-Object { $_.State -ne 'TimeWait' -and $_.State -ne 'CloseWait' -and $_.OwningProcess -gt 0 }
    foreach ($conn in $conns) {
        Write-Host "   Killing process tree PID=$($conn.OwningProcess) on port $targetPort (state=$($conn.State)) ..."
        & taskkill /T /F /PID $conn.OwningProcess 2>$null
    }
}

# Wait and verify ports are actually free (retry up to 30 seconds)
# Only check for LISTEN/ESTABLISHED - TIME_WAIT is safe to ignore (SO_REUSEADDR)
Write-Host "   Waiting for ports to be released..."
$maxWait = 30
for ($w = 0; $w -lt $maxWait; $w++) {
    $busy = $false
    foreach ($targetPort in $portsToFree) {
        $conns = Get-NetTCPConnection -LocalPort $targetPort -ErrorAction SilentlyContinue |
                 Where-Object { $_.State -eq 'Listen' -or $_.State -eq 'Established' -or $_.State -eq 'Bound' }
        if ($conns) { $busy = $true; break }
    }
    if (-not $busy) { break }
    Start-Sleep -Seconds 1
}
if ($busy) {
    Write-Err "Ports still occupied after ${maxWait}s. Please manually kill processes on ports: $($portsToFree -join ', ')"
    exit 1
}
Write-OK "Ports $($portsToFree -join ', ') are free"

# Set environment variables for the child process
$env:LLAMACPP_ROOT      = $CppDir
$env:MODEL_DIR          = $ModelDir
$env:REF_AUDIO          = $RefAudio
$env:PYTHONIOENCODING   = "utf-8"
$env:PYTHONUTF8         = "1"

# Build argument list
$pyArgs = "`"$ServerScript`" --llamacpp-root `"$CppDir`" --model-dir `"$ModelDir`" --port $Port --$Mode"

# Start background process
Push-Location $CppDir

Start-Process -FilePath $PythonBin `
              -ArgumentList $pyArgs `
              -WindowStyle Hidden `
              -RedirectStandardOutput $CPP_SERVER_LOG `
              -RedirectStandardError  $CPP_SERVER_ERR_LOG

Write-Host "   Waiting for inference service to start..."
Start-Sleep -Seconds 15

# Health check (retry a few times)
$healthy = $false
for ($i = 0; $i -lt 3; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:$Port/health" -TimeoutSec 5 -ErrorAction Stop
        $healthy = $true
        break
    } catch {
        Start-Sleep -Seconds 5
    }
}

if ($healthy) {
    Write-OK "C++ inference service started"
    Write-Host "   $resp"
} else {
    Write-Err "C++ inference service failed to start"
    Write-Host "   Log file: $CPP_SERVER_LOG"
    if (Test-Path $CPP_SERVER_LOG) {
        Write-Host "   --- Last 20 lines ---"
        Get-Content $CPP_SERVER_LOG -Tail 20
    }
    if (Test-Path $CPP_SERVER_ERR_LOG) {
        Write-Host "   --- Stderr ---"
        Get-Content $CPP_SERVER_ERR_LOG -Tail 20
    }
    Pop-Location; exit 1
}

Pop-Location

# ==========================================================
# [7/7] Register Inference Service
# ==========================================================
Write-Step "7/7" "Registering inference service..."

$registerBody = @{
    ip           = $LOCAL_IP
    port         = $Port
    model_port   = $Port
    model_type   = "release"
    session_type = "release"
    service_name = "o45-cpp"
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "http://localhost:8021/api/inference/register" `
                  -Method POST `
                  -ContentType "application/json" `
                  -Body $registerBody `
                  -TimeoutSec 10 -ErrorAction Stop
    Write-OK "Inference service registered"
    Write-Host "   $result"
} catch {
    Write-Warn "Registration may have failed. Check backend service."
    Write-Host "   $($_.Exception.Message)"
}

# ==========================================================
# Done
# ==========================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "   Deployment complete!                 " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "   Service URLs:" -ForegroundColor Green
Write-Host "      Frontend Web UI :  http://localhost:3000"
Write-Host "      Backend API     :  http://localhost:8021"
Write-Host "      Inference       :  http://localhost:${Port}"
Write-Host "      LiveKit         :  ws://localhost:7880"
Write-Host ""
Write-Host "   Useful commands:" -ForegroundColor Green
Write-Host "      View Docker logs  :  cd `"$SCRIPT_DIR`"; docker compose logs -f"
Write-Host "      View inference log:  Get-Content `"$CPP_SERVER_LOG`" -Tail 50 -Wait"
Write-Host "      Stop Docker       :  cd `"$SCRIPT_DIR`"; docker compose down"
Write-Host "      Stop inference    :  Get-CimInstance Win32_Process | Where-Object { `$_.CommandLine -like '*minicpmo_cpp_http_server*' } | ForEach-Object { Stop-Process -Id `$_.ProcessId -Force }"
Write-Host ""

@echo off
cd /d "%~dp0"

echo ============================================
echo Starting LiveKit Server
echo ============================================
echo.

if not exist "livekit-server.exe" (
    echo ERROR: livekit-server.exe not found
    echo Please download from: https://github.com/livekit/livekit/releases
    pause
    exit /b 1
)

if not exist "livekit-windows.yaml" (
    echo ERROR: livekit-windows.yaml not found
    pause
    exit /b 1
)

tasklist | findstr "livekit-server" >nul
if %errorlevel% == 0 (
    echo WARN: LiveKit is already running
    pause
    exit /b 0
)

if not exist ".logs" mkdir ".logs"

echo Starting LiveKit...
start /B livekit-server.exe --config livekit-windows.yaml > .logs\livekit-windows.log 2>&1

timeout /t 3 /nobreak >nul

echo Checking ports...
netstat -an | findstr "LISTENING" | findstr ":7880" >nul
if %errorlevel% == 0 (
    echo OK: Port 7880 listening
) else (
    echo ERROR: Port 7880 not listening
)

netstat -an | findstr "LISTENING" | findstr ":7881" >nul
if %errorlevel% == 0 (
    echo OK: Port 7881 listening
) else (
    echo ERROR: Port 7881 not listening
)

echo.
echo LiveKit started!
echo   ws://127.0.0.1:7880
echo   127.0.0.1:7881
echo.
pause

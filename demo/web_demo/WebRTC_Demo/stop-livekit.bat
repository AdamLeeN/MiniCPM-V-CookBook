@echo off
echo Stopping LiveKit...
taskkill /F /IM livekit-server.exe >nul 2>&1
if %errorlevel% == 0 (
    echo OK: LiveKit stopped
) else (
    echo INFO: No LiveKit process found
)
pause

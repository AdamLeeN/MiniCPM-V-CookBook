@echo off
chcp 65001 >nul
echo ============================================
echo   MiniCPM-o Launcher 构建脚本
echo ============================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    exit /b 1
)

:: 安装依赖
echo [1/4] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    exit /b 1
)

:: 安装 PyInstaller
echo [2/4] 安装 PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    exit /b 1
)

:: 构建 EXE
echo [3/4] 构建 EXE...
pyinstaller launcher.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 构建失败
    exit /b 1
)

:: 复制额外文件
echo [4/4] 复制资源文件...
if not exist "dist\embedded" mkdir "dist\embedded"
xcopy /E /I /Y "..\demo\web_demo\WebRTC_Demo" "dist\embedded\WebRTC_Demo" >nul 2>&1

:: 创建用户数据目录
if not exist "dist\user_data" mkdir "dist\user_data"
if not exist "dist\user_data\logs" mkdir "dist\user_data\logs"

echo.
echo ============================================
echo   构建完成！
echo ============================================
echo.
echo 输出目录: %SCRIPT_DIR%dist
echo 可执行文件: %SCRIPT_DIR%dist\MiniCPM-o-Launcher.exe
echo.
pause

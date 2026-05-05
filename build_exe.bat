@echo off
setlocal
echo ========================================
echo  PostBridge - Windows Build
echo ========================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found
python --version

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found, please install Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js found
node --version

echo.
echo [1/5] Building frontend...
if not exist "%SCRIPT_DIR%postbridge_frontend" (
    echo [ERROR] Cannot find postbridge_frontend directory
    pause
    exit /b 1
)
cd /d "%SCRIPT_DIR%postbridge_frontend"

call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
)

call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)

REM Copy frontend dist to backend static
echo.
echo [2/5] Copying frontend files to backend...
if not exist "%SCRIPT_DIR%postbridge_backend\static" mkdir "%SCRIPT_DIR%postbridge_backend\static"
xcopy /E /I /Y dist\* "%SCRIPT_DIR%postbridge_backend\static\"

echo.
echo [3/5] Installing Python dependencies...
cd /d "%SCRIPT_DIR%postbridge_backend"
pip install -r requirements.txt -q
pip install pyinstaller -q

echo.
echo [4/5] Skipping database init (clean build)...

echo.
echo [5/5] Building EXE with PyInstaller...
pyinstaller --clean --noconfirm app.spec

cd /d "%SCRIPT_DIR%"

echo.
echo ========================================
echo  Build complete!
echo  Output: postbridge_backend\dist\
echo ========================================
echo.
echo Usage:
echo 1. Copy dist folder to target directory
echo 2. Make sure Chrome browser is installed
echo 3. Run EXE and visit http://localhost:5409
echo.
pause

@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ======================================================================
echo  Regex Stripper - Standalone Executable Builder (PyInstaller)
echo ======================================================================
echo.

REM Set UTF-8 encoding
chcp 65001 >nul

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv!
    echo Please ensure .venv is configured.
    pause
    exit /b 1
)

echo [1/4] Ensuring application icon is generated...
".venv\Scripts\python.exe" generate_icon.py
if errorlevel 1 (
    echo [WARNING] Icon generation encountered an issue, proceeding...
)

echo [2/4] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist\RegexStripper.exe" del /f /q "dist\RegexStripper.exe"

echo [3/4] Compiling standalone executable with assets, icons and presets...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name "RegexStripper" ^
    --icon "assets/app.ico" ^
    --add-data "assets;assets" ^
    --clean ^
    run.py

if errorlevel 1 (
    echo.
    echo [FAILED] PyInstaller build failed with error code %errorlevel%.
    pause
    exit /b %errorlevel%
)

echo.
echo ======================================================================
echo  [SUCCESS] Build Complete!
echo  Standalone Executable: dist\RegexStripper.exe
echo ======================================================================
echo.
pause
exit /b 0

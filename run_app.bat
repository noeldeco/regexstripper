@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ======================================================================
echo  Regex Stripper - Desktop Utility Launcher
echo ======================================================================

if not exist ".venv\Scripts\python.exe" goto NO_VENV

REM Set UTF-8 encoding
chcp 65001 >nul

echo [INFO] Starting Regex Stripper...
".venv\Scripts\python.exe" run.py %*
if errorlevel 1 goto RUN_ERROR
goto END

:NO_VENV
echo [ERROR] Virtual environment (.venv) not found!
echo Please create the virtual environment and install requirements:
echo   python -m venv .venv
echo   .\.venv\Scripts\pip install -r requirements.txt
pause
exit /b 1

:RUN_ERROR
echo.
echo [ERROR] Application exited with an error.
pause
exit /b 1

:END
exit /b 0


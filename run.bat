@echo off
title Omni - AI Life Companion
cd /d "%~dp0"

echo ========================================================
echo   ✦ Starting Omni — AI Life Companion ✦
echo ========================================================
echo.
echo Launching local server and web interface...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ========================================================
    echo   [ERROR] Application exited with an error.
    echo   If you see a dependency issue, run:
    echo   python -m pip install -r requirements.txt
    echo ========================================================
    echo.
    pause
)


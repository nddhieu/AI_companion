@echo off
title Build Omni - Standalone Desktop App
cd /d "%~dp0"

echo ========================================================
echo   ✦ Building Omni — AI Life Companion (.exe) ✦
echo ========================================================
echo.

echo 1. Ensuring PyInstaller is installed...
python -m pip install pyinstaller

echo.
echo 2. Packaging desktop application...
python -m PyInstaller --noconfirm --onedir --windowed --add-data "static;static" --name "Omni-Life-Companion" main.py

echo.
echo ========================================================
echo   Build complete! Output located at:
echo   dist\Omni-Life-Companion\Omni-Life-Companion.exe
echo ========================================================
echo.
pause

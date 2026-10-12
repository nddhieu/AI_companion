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
echo 2. Packaging desktop application (Single Standalone .exe)...
python -m PyInstaller --noconfirm --onefile --windowed --add-data "static;static" --name "Omni-Life-Companion" main.py

echo.
echo 3. Packaging directory bundle & creating release ZIP...
python -m PyInstaller --noconfirm --onedir --windowed --add-data "static;static" --name "Omni-Life-Companion-Folder" main.py

if exist "dist\Omni-Life-Companion-Folder" (
    powershell -Command "Compress-Archive -Path 'dist\Omni-Life-Companion-Folder\*' -DestinationPath 'dist\Omni-Life-Companion-v2.0.0-windows.zip' -Force"
)

echo.
echo ========================================================
echo   Build complete! Output files:
echo   1. Standalone Single EXE: dist\Omni-Life-Companion.exe (Run directly)
echo   2. Release Archive ZIP:   dist\Omni-Life-Companion-v2.0.0-windows.zip
echo ========================================================
echo.
pause


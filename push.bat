@echo off
title Push AI Companion to GitHub
cd /d "%~dp0"

echo ========================================================
echo   Pushing AI Companion to GitHub...
echo ========================================================
echo.

set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
if not exist "%GIT_CMD%" set "GIT_CMD=git"

"%GIT_CMD%" push -u origin main

echo.
echo ========================================================
echo   Done!
echo ========================================================
pause

@echo off
title Flight Tracker - Setup
echo ============================================
echo   Flight Tracker - Installing Dependencies
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Python found. Installing required packages...
echo.

pip install requests windows-toasts winotify

echo.
echo ============================================
echo   Setup complete!
echo   Run flight_tracker.bat to start the app.
echo ============================================
pause

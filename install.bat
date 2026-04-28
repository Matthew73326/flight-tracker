@echo off
title Flight Tracker - Installer
color 0A

echo.
echo  ================================================
echo    Flight Tracker - Installer
echo    github.com/Matthew73326/flight-tracker
echo  ================================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not found!
    echo.
    echo  Please install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Tick "Add Python to PATH" during install.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

echo  [OK] Python found.
echo.

:: Create install folder on Desktop
set INSTALL_DIR=%USERPROFILE%\Desktop\Flight Tracker
echo  [..] Creating folder: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul
echo  [OK] Folder created.
echo.

:: Download all files from GitHub
echo  [..] Downloading files from GitHub...
echo.

set BASE_URL=https://raw.githubusercontent.com/Matthew73326/flight-tracker/main

powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/flight_tracker.py' -OutFile '%INSTALL_DIR%\flight_tracker.py'" >nul 2>&1
echo  [OK] flight_tracker.py
powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/updater.py' -OutFile '%INSTALL_DIR%\updater.py'" >nul 2>&1
echo  [OK] updater.py
powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/version.json' -OutFile '%INSTALL_DIR%\version.json'" >nul 2>&1
echo  [OK] version.json
powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/setup_install.bat' -OutFile '%INSTALL_DIR%\setup_install.bat'" >nul 2>&1
echo  [OK] setup_install.bat
powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/flight_tracker.bat' -OutFile '%INSTALL_DIR%\flight_tracker.bat'" >nul 2>&1
echo  [OK] flight_tracker.bat
powershell -Command "Invoke-WebRequest -Uri '%BASE_URL%/Launch_FlightTracker.vbs' -OutFile '%INSTALL_DIR%\Launch_FlightTracker.vbs'" >nul 2>&1
echo  [OK] Launch_FlightTracker.vbs

echo.

:: Check downloads worked
if not exist "%INSTALL_DIR%\flight_tracker.py" (
    echo  [!] Download failed! Check your internet connection and try again.
    pause
    exit /b 1
)

:: Install Python dependencies
echo  [..] Installing Python dependencies...
pip install requests windows-toasts winotify >nul 2>&1
echo  [OK] Dependencies installed.
echo.

:: Create Desktop shortcut
echo  [..] Creating Desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Flight Tracker.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\Launch_FlightTracker.vbs"\"'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'Flight Tracker'; $s.Save()" >nul 2>&1
echo  [OK] Shortcut created on Desktop.
echo.

echo  ================================================
echo    Installation complete!
echo.
echo    A shortcut has been placed on your Desktop.
echo    Double-click "Flight Tracker" to launch.
echo  ================================================
echo.
pause

:: Launch the app
start "" wscript.exe "%INSTALL_DIR%\Launch_FlightTracker.vbs"

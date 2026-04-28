@echo off
cd /d "%~dp0"

:: Use pythonw.exe — runs Python with NO console window
start "" pythonw.exe flight_tracker.py

:: If pythonw fails, fall back to regular python
if errorlevel 1 (
    python flight_tracker.py
)

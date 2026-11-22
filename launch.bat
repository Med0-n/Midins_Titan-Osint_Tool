@echo off
cd /d "%~dp0"

title MIDINS TITAN OSINT - LAUNCHER
mode con: cols=85 lines=22
color 0b

echo ======================================================
echo           MIDINS TITAN : SYSTEM LAUNCHER
echo ======================================================
echo.
echo [INFO] Detected location: %cd%
echo.

:: 1. Python interpreter detection (venv or system)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

:: 2. Launch Flask server in separate window
echo [1/2] Starting Flask backend server...
start "TITAN_SERVER" cmd /k "%PY_CMD%" app.py

:: 3. Wait 3 seconds for server initialization
timeout /t 3 /nobreak > nul

:: 4. Automatically open browser
echo [2/2] Opening browser interface...
start http://127.0.0.1:5000

echo.
echo ======================================================
echo           MIDINS TITAN IS READY
echo ======================================================
echo Launcher will close in 5 seconds...
timeout /t 5 > nul
exit

@echo off
:: Cette commande permet de forcer le terminal à se situer dans le dossier du script
cd /d "%~dp0"

title TITAN OSINT - AUTO-DETECTION
mode con: cols=85 lines=22
color 05

echo ======================================================
echo           TITAN SYSTEM : FOLDER DETECTED
echo ======================================================
echo.
echo [INFO] Emplacement detected : %cd%
echo.

:: 1. Launching the Python server in a separate window
echo [1/2] Starting the Flask engine...
start "TITAN_SERVER" cmd /k python app.py

:: 2. Waiting 3 seconds for initialization
timeout /t 3 /nobreak > nul

:: 3. Automatically opening the browser
echo [2/2] Opening the graphical interface...
start http://127.0.0.1:5000

echo.
echo ======================================================
echo           TITAN IS READY - GOOD INVESTIGATION
echo ======================================================
echo This launcher will close in 5 seconds...
timeout /t 5 > nul
exit
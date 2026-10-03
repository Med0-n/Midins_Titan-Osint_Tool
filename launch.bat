@echo off
:: Cette commande permet de forcer le terminal à se situer dans le dossier du script
cd /d "%~dp0"

title TITAN OSINT - AUTO-DETECTION
mode con: cols=85 lines=22
color 05

echo ======================================================
echo           TITAN SYSTEM : FOLDER DETECTION
echo ======================================================
echo.
echo [INFO] Emplacement detected : %cd%
echo.

:: 1. Detection de l'interpreteur Python (venv ou systeme)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

:: 2. Lancement du serveur Python dans une fenetre separee
echo [1/2] Lancement du moteur Flask...
start "TITAN_SERVER" cmd /k "%PY_CMD%" app.py

:: 2. Attente de 3 secondes pour l'initialisation
timeout /t 3 /nobreak > nul

:: 3. Ouverture automatique du navigateur
echo [2/2] Ouverture de l'interface graphique...
start http://127.0.0.1:5000

echo.
echo ======================================================
echo           TITAN EST PRET - BONNE ENQUETE
echo ======================================================
echo Ce lanceur va se fermer dans 5 secondes...
timeout /t 5 > nul
exit

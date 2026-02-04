@echo off
:: Cette commande permet de forcer le terminal à se situer dans le dossier du script
cd /d "%~dp0"

title TITAN OSINT - AUTO-DETECTION
mode con: cols=85 lines=22
color 05

echo ======================================================
echo           TITAN SYSTEM : DETECTION DU DOSSIER
echo ======================================================
echo.
echo [INFO] Emplacement detecte : %cd%
echo.

:: 1. Lancement du serveur Python dans une fenetre separee
echo [1/2] Lancement du moteur Flask...
start "TITAN_SERVER" cmd /k python app.py

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
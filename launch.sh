#!/bin/bash
# Midins Titan OSINT Tool - Launcher Linux / macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================"
echo "          TITAN SYSTEM : LAUNCHER"
echo "======================================================"
echo ""
echo "[INFO] Emplacement : $SCRIPT_DIR"
echo ""

# Find Python executable (checks local venv first, then system python)
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
else
    echo "❌ Erreur: Python non trouvé dans le PATH."
    exit 1
fi

echo "[1/2] Démarrage du serveur Flask..."
$PYTHON_CMD app.py &
SERVER_PID=$!

# Attendre 2 secondes que le serveur s'initialise
sleep 2

echo "[2/2] Ouverture de l'interface graphique..."
URL="http://127.0.0.1:5000"

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 &
else
    echo "ℹ️  Veuillez ouvrir votre navigateur à l'adresse : $URL"
fi

echo ""
echo "======================================================"
echo "          TITAN EST PRÊT - BONNE ENQUÊTE"
echo "======================================================"
echo "Appuyez sur Ctrl+C pour arrêter le serveur."

trap "kill $SERVER_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait $SERVER_PID

#!/bin/bash
# Midins Titan OSINT Tool - Launcher Linux / macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================"
echo "          MIDINS TITAN : SYSTEM LAUNCHER"
echo "======================================================"
echo ""
echo "[INFO] Working directory: $SCRIPT_DIR"
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
    echo "❌ Error: Python not found in PATH."
    exit 1
fi

echo "[1/2] Starting Flask backend server..."
$PYTHON_CMD app.py &
SERVER_PID=$!

# Wait 2 seconds for server initialization
sleep 2

echo "[2/2] Opening browser interface..."
URL="http://127.0.0.1:5000"

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 &
else
    echo "ℹ️  Please open your browser at: $URL"
fi

echo ""
echo "======================================================"
echo "          MIDINS TITAN IS READY"
echo "======================================================"
echo "Press Ctrl+C to stop the server."

trap "kill $SERVER_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait $SERVER_PID

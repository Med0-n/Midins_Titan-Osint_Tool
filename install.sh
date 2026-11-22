#!/bin/bash
echo "🔧 Installing Midins Titan..."

# Auto-detect OS
if [ -f /etc/fedora-release ]; then
    echo "📦 Fedora detected"
    sudo dnf install -y libxml2-devel libxslt-devel python3-devel gcc python3-pip
elif [ -f /etc/debian_version ]; then
    echo "📦 Debian/Ubuntu detected"
    sudo apt update && sudo apt install -y libxml2-dev libxslt-dev python3-dev gcc python3-venv python3-pip
elif [ -f /etc/arch-release ]; then
    echo "📦 Arch detected"
    sudo pacman -S --noconfirm libxml2 libxslt python gcc python-pip
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 macOS detected"
    which brew >/dev/null && brew install libxml2 libxslt || echo "⚠️ Homebrew not found, skipping system deps"
fi

# Install Python deps (supports direct pip, PEP 668 override, or virtualenv)
echo "📦 Installing Python dependencies..."
if pip install -r requirements.txt 2>/dev/null; then
    echo "✅ Dependencies installed via pip."
elif pip install --break-system-packages -r requirements.txt 2>/dev/null; then
    echo "✅ Dependencies installed via pip (--break-system-packages)."
else
    echo "⚙️ Creating virtual environment (venv)..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
    echo "✅ Virtual environment created & dependencies installed in ./venv"
fi

echo "✅ Installation complete!"
echo "▶️  Run: ./launch.sh (or python3 app.py)"


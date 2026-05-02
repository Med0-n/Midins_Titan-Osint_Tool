#!/bin/bash
echo "🔧 Installing Midins Titan..."

# Auto-detect OS
if [ -f /etc/fedora-release ]; then
    echo "📦 Fedora detected"
    sudo dnf install -y libxml2-devel libxslt-devel python3-devel gcc
elif [ -f /etc/debian_version ]; then
    echo "📦 Debian/Ubuntu detected"
    sudo apt update && sudo apt install -y libxml2-dev libxslt-dev python3-dev gcc
elif [ -f /etc/arch-release ]; then
    echo "📦 Arch detected"
    sudo pacman -S --noconfirm libxml2 libxslt python gcc
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 macOS detected"
    which brew >/dev/null && brew install libxml2 libxslt || echo "⚠️ Homebrew not found, skipping system deps"
fi

# Install Python deps
pip install -r requirements.txt

echo "✅ Installation complete!"
echo "▶️  Run: python app.py"


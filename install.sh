#!/bin/bash

echo "🎵 Installing Oblique AV Synthesizer..."

# Check if Python 3.10+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.10 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "🚀 To run Oblique:"
    echo "   source venv/bin/activate"
    echo "   python main.py"
    echo ""
    echo "🎵 Enjoy creating audio-reactive visuals!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi 
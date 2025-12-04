#!/bin/bash
# Setup script for local AI music generation using MusicGen
# Run this script to install all dependencies

set -e

echo "========================================"
echo "  MusicGen Local Setup"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "Python version: $python_version"

# Detect if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "No virtual environment detected."
    echo "Creating one in ./venv..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Virtual environment activated: $VIRTUAL_ENV"
else
    echo "Using existing virtual environment: $VIRTUAL_ENV"
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Detect GPU
echo ""
echo "Detecting GPU..."

if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected!"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true
    echo ""
    echo "Installing PyTorch with CUDA support..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
elif [[ "$(uname)" == "Darwin" ]] && [[ "$(uname -m)" == "arm64" ]]; then
    echo "Apple Silicon detected!"
    echo "Installing PyTorch with MPS support..."
    pip install torch torchaudio
else
    echo "No GPU detected, using CPU (generation will be slower)"
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install transformers and other dependencies
echo ""
echo "Installing transformers and other dependencies..."
pip install transformers scipy

# Create output directory
mkdir -p output

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Usage examples:"
echo "  python music_generator.py 'upbeat electronic dance music'"
echo "  python music_generator.py --duration 15 'calm acoustic guitar'"
echo "  python music_generator.py --interactive"
echo ""
echo "Model will be downloaded on first run (~3.3GB for medium model)"
echo ""

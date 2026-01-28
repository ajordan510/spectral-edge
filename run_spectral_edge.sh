#!/bin/bash
# SpectralEdge Launcher Script for Linux/Mac
# This script launches the SpectralEdge application

echo "========================================"
echo "SpectralEdge - Signal Processing Suite"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

echo ""
echo "Launching SpectralEdge..."
echo ""

# Run the application
python3 -m spectral_edge.main

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Application exited with an error"
    exit 1
fi

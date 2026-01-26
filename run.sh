#!/bin/bash
# Launcher for SpectralEdge on Linux and macOS

# Ensure the script is run from the project root
cd "$(dirname "$0")"

# Define the virtual environment directory
VENV_DIR="venv"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to continue."
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please check your Python installation."
        exit 1
    fi
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
# We check for a flag file to avoid reinstalling every time
if [ ! -f "$VENV_DIR/.dependencies_installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please check your internet connection and requirements.txt."
        exit 1
    fi
    # Create flag file to indicate successful installation
    touch "$VENV_DIR/.dependencies_installed"
fi

# Launch the application
echo "Launching SpectralEdge..."
python3 -m spectral_edge.main

# Deactivate the virtual environment upon exit
deactivate


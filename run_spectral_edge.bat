@echo off
REM SpectralEdge Launcher Script for Windows
REM This script launches the SpectralEdge application

echo ========================================
echo SpectralEdge - Signal Processing Suite
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Launching SpectralEdge...
echo.

REM Run the application
python -m spectral_edge.main

if errorlevel 1 (
    echo.
    echo ERROR: Application exited with an error
    pause
)

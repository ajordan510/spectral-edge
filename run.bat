@echo off
REM Launcher for SpectralEdge on Windows

REM Ensure the script is run from the project root
cd /d "%~dp0"

REM Define the virtual environment directory
set VENV_DIR=venv

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3 to continue.
    exit /b 1
)

REM Create a virtual environment if it doesn't exist
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment. Please check your Python installation.
        exit /b 1
    )
)

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
REM We check for a flag file to avoid reinstalling every time
if not exist "%VENV_DIR%\.dependencies_installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install dependencies. Please check your internet connection and requirements.txt.
        exit /b 1
    )
    REM Create flag file to indicate successful installation
    echo. > "%VENV_DIR%\.dependencies_installed"
)

REM Launch the application
echo Launching SpectralEdge...
python -m spectral_edge.main

REM Deactivate the virtual environment upon exit
call "%VENV_DIR%\Scripts\deactivate.bat"

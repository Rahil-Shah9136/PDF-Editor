@echo off
echo ============================================
echo   PDF Editor - Setup and Launch
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo [1/2] Installing required packages...
pip install flask pymupdf
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install packages.
    echo Try running this as Administrator, or run manually:
    echo   pip install flask pymupdf
    pause
    exit /b 1
)

echo.
echo [2/2] Starting PDF Editor...
echo.
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C in this window to stop the server.
echo.
python app.py
pause

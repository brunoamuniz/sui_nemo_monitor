@echo off
echo ========================================
echo    SUI MONITOR - STARTING SYSTEM
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ first
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure it first
    echo See README.md for configuration details
    pause
    exit /b 1
)

echo Configuration file found!
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found!
    echo Please run install.bat first to create the virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
echo Checking dependencies...
pip list | findstr requests >nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
) else (
    echo Dependencies already installed!
)

echo.

REM Create cache directory if it doesn't exist
if not exist "cache" mkdir cache

echo ========================================
echo    STARTING CONTINUOUS MONITORING
echo ========================================
echo.
echo Press Ctrl+C to stop monitoring
echo.

REM Start monitoring
python main.py --continuous

echo.
echo Monitoring finished.
pause

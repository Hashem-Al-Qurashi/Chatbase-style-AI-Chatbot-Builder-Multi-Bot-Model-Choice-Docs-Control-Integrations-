@echo off
echo ========================================
echo    Chatava Local Setup for Windows
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo Python and Node.js found!
echo.

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate venv and install dependencies
echo Installing Python dependencies (this takes a few minutes first time)...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

REM Create local env file
if not exist ".env.local" (
    echo Creating local environment file...
    copy .env.local.template .env.local >nul 2>&1
)

REM Run migrations
echo Setting up database...
set DATABASE_URL=sqlite:///db.sqlite3
set CELERY_TASK_ALWAYS_EAGER=True
set DEBUG=True
set SECRET_KEY=local-dev-secret-key-not-for-production
python manage.py migrate --run-syncdb

echo.
echo ========================================
echo    Setup complete!
echo ========================================
echo.
echo To start the app, run: START_APP.bat
echo.
pause

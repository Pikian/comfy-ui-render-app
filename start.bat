@echo off
echo Starting ComfyUI Middleware...

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo Choose an option:
echo 1. Start server locally
echo 2. Start server with ngrok (public access)
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    start cmd /k "uvicorn main:app --host 0.0.0.0 --port 8001"
    echo Server started at http://localhost:8001
) else if "%choice%"=="2" (
    start cmd /k "python start_with_ngrok.py"
    echo Server starting with ngrok...
) else (
    echo Invalid choice
    pause
    exit /b 1
)

echo Press Ctrl+C to stop the server
pause 
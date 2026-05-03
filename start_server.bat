@echo off
title AczWiki Server

cd /d "%~dp0"

echo.
echo  ================================================
echo   AczWiki - Internal Knowledge Base
echo  ================================================
echo.

:: Detect local IP from ipconfig
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set RAW_IP=%%a
    goto :found_ip
)
:found_ip
:: Trim leading space
set LOCAL_IP=%RAW_IP: =%

echo   Server starting...
echo.
echo   Local:   http://localhost:5000
echo   Network: http://%LOCAL_IP%:5000
echo.
echo   Share this with your teammates:
echo   --^> http://%LOCAL_IP%:5000
echo.
echo   Default login: admin / admin123
echo   Press Ctrl+C to stop the server.
echo  ================================================
echo.

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo   Found venv, activating...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo   Found .venv, activating...
    call .venv\Scripts\activate.bat
) else (
    echo   No venv found, using system Python.
)

echo.
python app.py

echo.
echo   Server stopped. Press any key to close.
pause >nul

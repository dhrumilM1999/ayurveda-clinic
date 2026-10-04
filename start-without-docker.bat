@echo off
REM Starts the clinic software WITHOUT Docker (for trying it out on this PC).
REM Uses Python + Node installed on Windows and a simple file database
REM (backend\local.sqlite3) instead of PostgreSQL. Demo data only.
REM To stop: close the two black windows "Clinic BACKEND" and "Clinic SCREENS".
title Ayurveda Clinic - Start (without Docker)
cd /d "%~dp0"
echo.
echo  ===================================================
echo     Starting the Ayurveda Clinic (without Docker)...
echo  ===================================================
echo.

where python >nul 2>nul
if errorlevel 1 goto nopython
where npm >nul 2>nul
if errorlevel 1 goto nonode

REM Settings for this mode (the .env file is used only by Docker)
set APP_ENV=development
set DJANGO_DEBUG=true
set SHOW_DEV_OTP_ON_SCREEN=true
set DEMO_MODE=true
set SMS_PROVIDER=console
set EMAIL_HOST=localhost
set VITE_PROXY_TARGET=http://127.0.0.1:8000

if exist "backend\.venv\Scripts\python.exe" goto venvready
echo  First time: preparing Python (1-3 minutes)...
python -m venv backend\.venv
if errorlevel 1 goto failed
:venvready
echo  Checking Python packages...
backend\.venv\Scripts\python -m pip install -q --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 goto failed

echo  Updating the database...
backend\.venv\Scripts\python backend\manage.py migrate --noinput -v 0
if errorlevel 1 goto failed
backend\.venv\Scripts\python backend\manage.py ensure_defaults
if errorlevel 1 goto failed
backend\.venv\Scripts\python backend\manage.py seed_demo --if-empty
if errorlevel 1 goto failed

if exist "frontend\node_modules" goto nodeready
echo  First time: downloading screen packages (1-3 minutes)...
pushd frontend
call npm install --no-audit --no-fund
popd
:nodeready

start "Clinic BACKEND - keep open" cmd /k backend\.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
start "Clinic SCREENS - keep open" cmd /k "cd frontend && npm run dev"

echo  Waiting for the app to get ready...
set /a tries=0
:waitapp
timeout /t 3 /nobreak >nul
set /a tries+=1
curl -s -f -o nul http://127.0.0.1:8000/api/v1/health/
if errorlevel 1 goto notyet
curl -s -o nul http://localhost:5173/
if errorlevel 1 goto notyet
goto ready
:notyet
if %tries% GEQ 60 goto slow
goto waitapp

:ready
echo.
echo  READY!  Opening http://localhost:5173
echo  Demo password for all users: Ayur@Demo2026   (e.g. admin, doctor1, reception1)
echo  The OTP is shown on the login screen.
echo  To stop: close the two windows "Clinic BACKEND" and "Clinic SCREENS".
start "" http://localhost:5173
pause
exit /b 0

:nopython
echo  Python is not installed. Install it from https://www.python.org/downloads/
pause
exit /b 1
:nonode
echo  Node.js is not installed. Install it from https://nodejs.org/
pause
exit /b 1
:failed
echo.
echo  Something went wrong. Copy the text above and paste it to Claude Code with "fix this".
pause
exit /b 1
:slow
echo  The app is taking very long. Look at the two black windows for red error text.
pause
exit /b 1

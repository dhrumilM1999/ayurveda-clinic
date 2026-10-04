@echo off
REM SAFE TO EDIT: the messages below. Starts the clinic software and opens the browser.
title Ayurveda Clinic - Start
cd /d "%~dp0"
echo.
echo  ===================================================
echo     Starting the Ayurveda Clinic software...
echo  ===================================================
echo.

where docker >nul 2>nul
if errorlevel 1 goto nodocker

docker info >nul 2>nul
if not errorlevel 1 goto dockerready
echo  Docker Desktop is not running. Opening it now, please wait...
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
set /a tries=0
:waitdocker
timeout /t 5 /nobreak >nul
set /a tries+=1
docker info >nul 2>nul
if not errorlevel 1 goto dockerready
if %tries% GEQ 36 goto dockerslow
goto waitdocker

:dockerready
if exist ".env" goto envready
copy ".env.example" ".env" >nul
echo  Created your settings file ".env" (a copy of .env.example).
:envready

echo  Building and starting... The FIRST time this downloads a lot and can take 5-15 minutes.
docker compose up -d --build
if errorlevel 1 goto failed

echo.
echo  Waiting for the app to get ready...
set /a tries=0
:waitapp
timeout /t 5 /nobreak >nul
set /a tries+=1
curl -s -f -o nul http://localhost:8000/api/v1/health/
if errorlevel 1 goto notyet
curl -s -o nul http://localhost:5173/
if errorlevel 1 goto notyet
goto ready
:notyet
if %tries% GEQ 180 goto slow
<nul set /p "=."
goto waitapp

:ready
echo.
echo.
echo  ===================================================
echo     READY!  Opening http://localhost:5173
echo  ===================================================
echo.
echo   Sample logins (made-up data). Password for all: Ayur@2026
echo     admin        - clinic owner, all access (needs OTP)
echo     doctor1      - Dr. Asha Mehta (needs OTP)
echo     doctor2      - Dr. Ravi Patel (needs OTP)
echo     reception1   - receptionist
echo     therapist1   - therapist
echo     pharmacist1  - pharmacist
echo.
echo   The OTP is shown on the login screen (practice mode) and in logs.bat.
echo   Other addresses:  API  http://localhost:8000/api/v1/
echo                     Admin http://localhost:8000/admin/
echo                     Test email inbox http://localhost:8025
echo.
start "" http://localhost:5173
echo  You can close this window. The app keeps running until you run stop.bat.
pause
exit /b 0

:nodocker
echo  Docker is not installed on this computer.
echo  Please install Docker Desktop - see docs\START_HERE_WINDOWS.md
pause
exit /b 1

:dockerslow
echo  Docker Desktop did not start in 3 minutes. Open it yourself, wait for
echo  "Engine running", then double-click start.bat again.
pause
exit /b 1

:failed
echo.
echo  Something went wrong while starting. Copy the red text above and
echo  paste it to Claude Code with "fix this". See docs\TROUBLESHOOTING.md
pause
exit /b 1

:slow
echo.
echo  The app is taking very long to start. Run logs.bat to see what is happening.
echo  See docs\TROUBLESHOOTING.md
pause
exit /b 1

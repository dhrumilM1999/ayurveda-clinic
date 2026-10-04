@echo off
REM Stops the clinic software. Your data is kept (it lives in Docker volumes).
title Ayurveda Clinic - Stop
cd /d "%~dp0"
echo.
echo  Stopping the Ayurveda Clinic software...
docker compose down
if errorlevel 1 (
  echo  Could not stop. Is Docker Desktop running?
) else (
  echo  Stopped. Your data is safe. Run start.bat to start again.
)
echo.
pause

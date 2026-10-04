@echo off
REM Deletes ALL data and creates fresh sample data. Only works when DEMO_MODE=true in .env.
REM NEVER use this once real patient data has been entered.
title Ayurveda Clinic - Reset sample data
cd /d "%~dp0"
echo.
echo  ==============================================================
echo    WARNING: this DELETES ALL DATA and creates fresh sample data.
echo    Only for testing. Never use it with real patients.
echo  ==============================================================
echo.
set /p answer="  Type YES (in capitals) to continue: "
if not "%answer%"=="YES" (
  echo  Cancelled. Nothing was changed.
  pause
  exit /b 0
)
docker compose exec backend python manage.py seed_demo --reset
if errorlevel 1 (
  echo.
  echo  Reset failed. Is the app running - start.bat? Is DEMO_MODE=true in .env?
) else (
  echo.
  echo  Done. Fresh sample data is ready. Log in again at http://localhost:5173
)
pause

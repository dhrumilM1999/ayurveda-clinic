@echo off
REM SAFE TO EDIT: the messages. Practice robot: sees today's patients at their appointment time (fake patients only).
title Ayurveda Clinic - Practice robot
cd /d "%~dp0"
echo.
echo  ===================================================
echo     Practice robot: it checks in, examines, prescribes
echo     and gives medicines to today's sample patients.
echo     Medicine stock goes down, so you can test the
echo     stock alerts. Close this window to stop.
echo  ===================================================
echo.
echo  [1] Every patient at the time of the appointment (keep this window open)
echo  [2] Do ALL of today's patients right now
echo.
set /p choice= Type 1 or 2 and press Enter: 
if "%choice%"=="2" (
  docker compose exec -T backend python manage.py run_demo_doctor_bot --all-now
) else (
  docker compose exec -T backend python manage.py run_demo_doctor_bot
)
echo.
pause

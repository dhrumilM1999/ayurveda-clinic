@echo off
REM Shows what the app is doing (messages and errors). Login OTPs appear here too.
REM Usage: logs.bat            - backend and frontend
REM        logs.bat backend    - only the backend
title Ayurveda Clinic - Logs
cd /d "%~dp0"
echo.
echo  Showing live messages. Look for "SMS (console" to find a login OTP.
echo  Press Ctrl+C to stop watching (the app keeps running).
echo.
if "%~1"=="" (
  docker compose logs -f --tail 200 backend frontend
) else (
  docker compose logs -f --tail 200 %*
)
pause

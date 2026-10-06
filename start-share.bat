@echo off
REM SHARE MODE: start the clinic software so a phone / another laptop on the same Wi-Fi can open it.
REM To go back to private (this laptop only), double-click start.bat again.
cd /d "%~dp0"
echo.
echo  Starting the clinic software in SHARE mode...
docker compose -f docker-compose.yml -f docker-compose.share.yml up -d
if errorlevel 1 (
  echo.
  echo  Something went wrong. Is Docker Desktop running? Open it, wait 1 minute, and try again.
  pause
  exit /b 1
)
for /f %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*' } | Select-Object -First 1).IPAddress"') do set MYIP=%%i
echo.
echo  ==================================================================
echo   Wait about 1 minute, then on the PHONE (same Wi-Fi) open:
echo.
echo        http://%MYIP%:5173
echo.
echo   Login: admin  (OTP is shown in the yellow box on the login screen)
echo   Only demo data. Share only on a Wi-Fi you trust.
echo   When finished, double-click start.bat to go back to private mode.
echo  ==================================================================
echo.
start http://localhost:5173
pause

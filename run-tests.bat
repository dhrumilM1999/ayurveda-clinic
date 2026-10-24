@echo off
REM Runs the automatic tests on the LOCAL database (never on the live one).
REM Usage: run-tests.bat            (all tests)    run-tests.bat apps/billing   (one folder)
setlocal
set LOCALPW=
for /f "usebackq tokens=1,* delims==" %%a in (".env.local-db") do if "%%a"=="POSTGRES_PASSWORD" set LOCALPW=%%b
docker compose exec -T -e POSTGRES_HOST=db -e POSTGRES_USER=ayurveda -e POSTGRES_DB=ayurveda -e POSTGRES_SSLMODE= -e POSTGRES_PASSWORD=%LOCALPW% backend python -m pytest -q -p no:cacheprovider %*
endlocal

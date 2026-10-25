@echo off
REM Makes sure the free local AI (Ollama) is running and has the translation model loaded in memory,
REM so the "Translate" button answers in a few seconds instead of waiting for the model to start.
REM Runs by itself from start.bat. If Ollama is not installed it does nothing (the app works without it).
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
where ollama >nul 2>nul
if errorlevel 1 exit /b 0

set "MODEL=qwen2.5:3b"
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\.env") do if "%%a"=="OLLAMA_MODEL" set "MODEL=%%b"

curl -s -m 2 -o nul http://localhost:11434/api/tags
if not errorlevel 1 goto running
start "" /min ollama serve
set /a tries=0
:wait
timeout /t 2 /nobreak >nul
set /a tries+=1
curl -s -m 2 -o nul http://localhost:11434/api/tags
if not errorlevel 1 goto running
if %tries% GEQ 15 exit /b 0
goto wait

:running
REM Load the model and keep it in memory (keep_alive -1), generating nothing
curl -s -m 180 -o nul http://localhost:11434/api/generate -d "{\"model\":\"%MODEL%\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":-1,\"options\":{\"num_predict\":1}}"
exit /b 0

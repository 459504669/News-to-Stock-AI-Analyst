@echo off
chcp 65001 >nul 2>&1
title News-to-Stock AI Analyst

echo ============================================================
echo   News-to-Stock AI Analyst
echo ============================================================
echo.

:: ---- Find Python ----
set "PYTHON_CMD="
for %%p in ("python" "python3" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe") do (
    if not defined PYTHON_CMD (
        %%~p --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=%%~p"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python not found!
    echo Install Python 3.10+: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ---- Create venv ----
if exist "venv\Scripts\activate.bat" goto :skip_venv_create
echo [SETUP] Creating virtual environment...
%PYTHON_CMD% -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)
echo [OK]   venv created
goto :after_venv

:skip_venv_create
echo [OK]   venv exists

:after_venv

:: ---- Activate ----
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv
    pause
    exit /b 1
)
echo [OK]   venv activated

:: ---- Install deps ----
if exist "venv\.pip_installed" goto :skip_pip
echo.
echo [SETUP] Installing dependencies...
echo.
pip install -r requirements.txt
echo installed > venv\.pip_installed
echo [OK]   Dependencies installed
goto :after_pip

:skip_pip
echo [OK]   Dependencies ready

:after_pip

:: ---- Check .env ----
if exist ".env" goto :skip_env
echo [SETUP] First run - creating .env config file...
copy .env.example .env >nul 2>&1
echo.
echo ============================================================
echo [IMPORTANT] Please edit .env and add your LLM API Key!
echo   Providers: openai / qwen / anthropic / wenxin
echo   Example: QWEN_API_KEY=your_key_here
echo ============================================================
notepad .env
echo Done. Run start.vbs again to launch the server.
pause
exit /b 0

:skip_env

:: ---- Create dirs ----
if not exist "data" mkdir data
if not exist "output" mkdir output
if not exist "output\images" mkdir output\images
if not exist "logs" mkdir logs

:: ---- Launch ----
echo.
echo ============================================================
echo   Server starting...
echo   Homepage:  http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Press Ctrl+C to stop
echo ============================================================
echo.

venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8000 --reload

pause

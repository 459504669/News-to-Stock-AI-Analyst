@echo off
chcp 65001 >nul 2>&1
title News-to-Stock AI Analyst

echo ============================================================
echo   News-to-Stock AI Analyst v0.3.0
echo ============================================================
echo.

:: ---- Find Python ----
set "PYTHON_CMD="
for %%p in ("python" "python3" "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe") do (
    if not defined PYTHON_CMD (
        %%~p --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=%%~p"
    )
)
if not defined PYTHON_CMD (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ---- Create venv ----
if exist "venv\Scripts\activate.bat" goto :skip_venv_create
echo [SETUP] Creating venv...
%PYTHON_CMD% -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)
:skip_venv_create

:: ---- Activate ----
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv
    pause
    exit /b 1
)
echo [OK]   venv activated

:: ---- Install / update deps (idempotent) ----
echo [SETUP] Checking dependencies...
venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] pip install returned non-zero, but continuing...
)
echo [OK]   Dependencies ready

:: ---- Check .env exists ----
if not exist ".env" goto :no_env

:: ---- Validate .env configuration ----
echo [SETUP] Checking API configuration...
call :check_env_config
if errorlevel 1 goto :config_error

:: ---- Create dirs ----
if not exist "data" mkdir data
if not exist "output" mkdir output
if not exist "output\images" mkdir output\images
if not exist "logs" mkdir logs

:: ---- Launch API server ----
echo.
echo ============================================================
echo   Starting server...
echo   API Docs:  http://localhost:8000/docs
echo   Daily Report: http://localhost:8000/api/daily-report/image
echo.
echo   Press Ctrl+C to stop
echo ============================================================
echo.

venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8000 --reload

pause
exit /b 0

:: ============================================================
:: Subroutine: Check .env configuration
:: Returns 0 if OK, 1 if error
:: ============================================================
:check_env_config
set "CONFIG_OK=1"
set "PROVIDER="
set "MODEL="
set "API_KEY="

:: Read DEFAULT_LLM_PROVIDER from .env
for /f "tokens=1,* delims==" %%a in ('findstr /R "^DEFAULT_LLM_PROVIDER=" .env') do set "PROVIDER=%%b"
for /f "tokens=1,* delims==" %%a in ('findstr /R "^DEFAULT_LLM_MODEL=" .env') do set "MODEL=%%b"

:: Check provider
if not defined PROVIDER (
    echo [CONFIG ERROR] DEFAULT_LLM_PROVIDER not set in .env
    set "CONFIG_OK=0"
    goto :check_env_end
)

:: Check model name (common invalid values)
if "%MODEL%"=="auto" (
    echo [CONFIG ERROR] DEFAULT_LLM_MODEL=auto is invalid!
    echo   Valid qwen models: qwen-max, qwen-plus, qwen-turbo
    echo   Valid openai models: gpt-4o, gpt-4o-mini, gpt-3.5-turbo
    set "CONFIG_OK=0"
    goto :check_env_end
)
if "%MODEL%"=="your_model_name_here" (
    echo [CONFIG ERROR] DEFAULT_LLM_MODEL is still a placeholder!
    set "CONFIG_OK=0"
    goto :check_env_end
)

:: Check API Key based on provider
if "%PROVIDER%"=="qwen" (
    for /f "tokens=1,* delims==" %%a in ('findstr /R "^QWEN_API_KEY=" .env') do set "API_KEY=%%b"
    if not defined API_KEY (
        echo [CONFIG ERROR] QWEN_API_KEY not found in .env
        set "CONFIG_OK=0"
        goto :check_env_end
    )
    if "%API_KEY%"=="your_qwen_api_key_here" (
        echo [CONFIG ERROR] QWEN_API_KEY is still a placeholder!
        set "CONFIG_OK=0"
        goto :check_env_end
    )
    if "%API_KEY%"=="your_key" (
        echo [CONFIG ERROR] QWEN_API_KEY is still a placeholder!
        set "CONFIG_OK=0"
        goto :check_env_end
    )
    echo [OK]   Config: provider=%PROVIDER%, model=%MODEL%
)

if "%PROVIDER%"=="openai" (
    for /f "tokens=1,* delims==" %%a in ('findstr /R "^OPENAI_API_KEY=" .env') do set "API_KEY=%%b"
    if not defined API_KEY (
        echo [CONFIG ERROR] OPENAI_API_KEY not found in .env
        set "CONFIG_OK=0"
        goto :check_env_end
    )
    if "%API_KEY%"=="your_openai_api_key_here" (
        echo [CONFIG ERROR] OPENAI_API_KEY is still a placeholder!
        set "CONFIG_OK=0"
        goto :check_env_end
    )
    echo [OK]   Config: provider=%PROVIDER%, model=%MODEL%
)

:check_env_end
if "%CONFIG_OK%"=="1" exit /b 0
exit /b 1

:: ============================================================
:: Subroutine: Config error handler
:: ============================================================
:config_error
echo.
echo ============================================================
echo [IMPORTANT] Configuration error detected!
echo.
echo Please edit .env and fix the settings above.
echo The notepad will open automatically.
echo.
echo Common fixes:
echo   1. If using Qwen:   QWEN_API_KEY=sk-xxx  DEFAULT_LLM_MODEL=qwen-max
necho   2. If using OpenAI: OPENAI_API_KEY=sk-xxx  DEFAULT_LLM_MODEL=gpt-4o
echo ============================================================
echo.
notepad .env
echo.
echo Configuration editor closed.
echo Please save .env and run start.vbs again.
pause
exit /b 1

:: ============================================================
:: Subroutine: No .env file
:: ============================================================
:no_env
echo [SETUP] Creating .env from template...
copy .env.example .env >nul 2>&1
echo.
echo ============================================================
echo [IMPORTANT] .env created! Please edit it and add your API Key.
echo   Example: QWEN_API_KEY=sk-xxx
echo            DEFAULT_LLM_PROVIDER=qwen
echo            DEFAULT_LLM_MODEL=qwen-max
echo ============================================================
notepad .env
echo Done. Run start.vbs again.
pause
exit /b 0

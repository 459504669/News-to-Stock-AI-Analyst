@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title News-to-Stock AI Analyst

echo ============================================================
echo   News-to-Stock AI Analyst  一键启动
echo ============================================================
echo.

:: ---- 1. 查找 Python ----
set "PYTHON_CMD="

:: 尝试常见路径
for %%p in (
    "python"
    "python3"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
) do (
    if not defined PYTHON_CMD (
        %%~p --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=%%~p"
        )
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] 未找到 Python！
    echo.
    echo 请先安装 Python 3.10 或更高版本:
    echo   https://www.python.org/downloads/
    echo.
    echo 安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%  (%PYTHON_CMD%)

:: ---- 2. 创建虚拟环境 ----
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [SETUP] 正在创建虚拟环境（首次可能需要几十秒）...
    %PYTHON_CMD% -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] 创建虚拟环境失败
        echo 请尝试手动运行: %PYTHON_CMD% -m venv venv
        pause
        exit /b 1
    )
    echo [OK]   虚拟环境已创建
) else (
    echo [OK]   虚拟环境已存在
)

:: ---- 3. 激活虚拟环境 ----
call venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo [ERROR] 激活虚拟环境失败
    pause
    exit /b 1
)
echo [OK]   虚拟环境已激活

:: ---- 4. 安装依赖 ----
if not exist "venv\.pip_installed" (
    echo.
    echo [SETUP] 正在安装依赖（首次可能需要 1-2 分钟）...
    echo.
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo.
        echo [WARN] 部分依赖安装失败，尝试继续启动...
    )
    echo.
    echo [OK]   依赖安装完成
    echo installed > venv\.pip_installed
) else (
    echo [OK]   依赖已安装（如需重装，删除 venv\.pip_installed 后重新运行）
)

:: ---- 5. 检查 .env ----
if not exist ".env" (
    echo.
    echo [SETUP] 首次运行，创建 .env 配置文件...
    copy .env.example .env >nul 2>&1
    echo.
    echo ============================================================
    echo [IMPORTANT] 请编辑 .env 文件，填入你的 LLM API Key！
    echo.
    echo   支持的提供商: openai / qwen / anthropic / wenxin
    echo   最少填一项 Key，例如:
    echo     QWEN_API_KEY=你的通义千问Key
    echo     DEFAULT_LLM_PROVIDER=qwen
    echo     DEFAULT_LLM_MODEL=qwen-max
    echo ============================================================
    echo.
    echo 即将打开 .env 文件，编辑保存后关闭记事本即可...
    echo.
    notepad .env
    echo.
    echo .env 已配置。重新运行 start.bat 启动服务。
    pause
    exit /b 0
)

:: ---- 6. 创建必要目录 ----
if not exist "data"    mkdir data
if not exist "output"    mkdir output
if not exist "output\images" mkdir output\images
if not exist "logs"    mkdir logs

:: ---- 7. 启动服务 ----
echo.
echo ============================================================
echo   API 服务启动中...
echo.
echo   服务首页:  http://localhost:8000
echo   API 文档:  http://localhost:8000/docs
echo.
echo   按 Ctrl+C 停止服务
echo ============================================================
echo.

venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo [INFO] 服务已停止
pause

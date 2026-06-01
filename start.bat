@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title News-to-Stock AI Analyst

echo ============================================================
echo   News-to-Stock AI Analyst  一键启动
echo ============================================================
echo.

:: ---- 1. 检查 Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.10+
    echo         下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ---- 2. 创建虚拟环境 ----
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [SETUP] 正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [OK]   虚拟环境已创建
) else (
    echo [OK]   虚拟环境已存在
)

:: ---- 3. 激活并安装依赖 ----
call venv\Scripts\activate.bat

if not exist "venv\.pip_installed" (
    echo.
    echo [SETUP] 正在安装依赖...
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [WARN] 部分依赖安装失败，尝试继续...
    )
    echo [OK]   依赖安装完成
    echo installed > venv\.pip_installed
) else (
    echo [OK]   依赖已安装
)

:: ---- 4. 检查 .env ----
if not exist ".env" (
    echo.
    echo [SETUP] 首次运行，创建 .env 配置文件...
    copy .env.example .env >nul 2>&1
    echo [IMPORTANT] 请编辑 .env 文件，填入你的 LLM API Key！
    echo.
    echo   支持的 LLM 提供商: openai / anthropic / qwen / wenxin
    echo   必填项: OPENAI_API_KEY 或 QWEN_API_KEY 或其他对应 Key
    echo.
    echo   编辑后重新运行此脚本即可启动服务。
    echo.
    notepad .env
    pause
    exit /b 0
)

:: ---- 5. 创建必要目录 ----
if not exist "data"    mkdir data
if not exist "output" mkdir output
if not exist "output\images" mkdir output\images
if not exist "logs"   mkdir logs

:: ---- 6. 启动服务 ----
echo.
echo ============================================================
echo   API 服务启动中...
echo   访问地址:
echo     http://localhost:8000        - 服务首页
echo     http://localhost:8000/docs    - API 文档 (Swagger UI)
echo
echo   按 Ctrl+C 停止服务
echo ============================================================
echo.

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

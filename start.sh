#!/usr/bin/env bash
# News-to-Stock AI Analyst  一键启动脚本 (Linux / macOS)

set -e

echo "============================================================"
echo "  News-to-Stock AI Analyst  一键启动"
echo "============================================================"
echo ""

# ---- 1. 检查 Python ----
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "[ERROR] 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
PYVER=$($PYTHON --version 2>&1)
echo "[OK] $PYVER"

# ---- 2. 创建虚拟环境 ----
if [ ! -f "venv/bin/activate" ]; then
    echo ""
    echo "[SETUP] 正在创建虚拟环境..."
    $PYTHON -m venv venv
    echo "[OK]   虚拟环境已创建"
else
    echo "[OK]   虚拟环境已存在"
fi

# ---- 3. 激活并安装依赖 ----
source venv/bin/activate

if [ ! -f "venv/.pip_installed" ]; then
    echo ""
    echo "[SETUP] 正在安装依赖..."
    pip install -r requirements.txt -q || echo "[WARN] 部分依赖安装失败，尝试继续..."
    echo "[OK]   依赖安装完成"
    touch venv/.pip_installed
else
    echo "[OK]   依赖已安装"
fi

# ---- 4. 检查 .env ----
if [ ! -f ".env" ]; then
    echo ""
    echo "[SETUP] 首次运行，创建 .env 配置文件..."
    cp .env.example .env
    echo "[IMPORTANT] 请编辑 .env 文件，填入你的 LLM API Key！"
    echo ""
    echo "  支持的 LLM 提供商: openai / anthropic / qwen / wenxin"
    echo "  必填项: OPENAI_API_KEY 或 QWEN_API_KEY 或其他对应 Key"
    echo ""
    echo "  编辑后重新运行此脚本即可启动服务。"
    echo ""
    ${EDITOR:-nano} .env
    exit 0
fi

# ---- 5. 创建必要目录 ----
mkdir -p data output/images logs

# ---- 6. 启动服务 ----
echo ""
echo "============================================================"
echo "  API 服务启动中..."
echo "  访问地址:"
echo "    http://localhost:8000        - 服务首页"
echo "    http://localhost:8000/docs    - API 文档 (Swagger UI)"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

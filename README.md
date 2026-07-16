# News-to-Stock AI Analyst 📈

> AI 驱动的实时新闻股市分析工具 —— 让新闻成为你的投资信号

## ✨ 项目简介

**News-to-Stock AI Analyst** 是一个基于大语言模型的实时新闻股市分析工具。它自动抓取国内外重大新闻，通过 AI 模拟资深投资专家视角进行深度分析，判断每条新闻对股市的影响倾向（利好/利空/中性），并给出具体的投资方向建议，最终生成一张信息丰富、视觉美观的分析可视化图片。

## 🎯 核心亮点

- 🌐 **实时新闻抓取** — 自动聚合全球主流财经媒体头条
- 🤖 **AI 专家分析** — 基于 LLM 的深度分析，模拟 20 年经验投资专家视角
- ⚡ **影响评级** — 5 档量化评分：强烈利空 / 利空 / 中性 / 利好 / 强烈利好
- 🎯 **投资方向推荐** — 给出受益板块、标的建议及风险提示
- 🖼️ **单图输出** — 所有分析结果整合到一张美观的信息图中
- 🔌 **API 支持** — 提供 REST API 接口供其他项目调用

## 🚀 快速开始

### 方式一：一键启动（推荐）

双击运行即可，脚本会自动完成环境配置：

**Windows:**
```
双击 start.bat
```

**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

首次运行时，脚本会自动：
1. 检查 Python 环境
2. 创建虚拟环境并安装依赖
3. 创建 `.env` 配置文件并打开编辑器，提示你填入 API Key
4. 第二次运行直接启动服务

### 方式二：手动安装

```bash
# 1. 克隆项目
git clone https://github.com/459504669/新闻抓取AI分析.git
cd 新闻抓取AI分析

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key（必填项见下方说明）

# 6. 启动服务
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 必填配置

编辑 `.env` 文件，至少配置一项 LLM API Key：

| 提供商 | 环境变量 | 模型示例 |
|--------|---------|---------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| 阿里通义千问 | `QWEN_API_KEY` | `qwen-max` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| 百度文心一言 | `WENXIN_API_KEY` | `ernie-bot-4` |

然后在 `.env` 中设置默认提供商：
```
DEFAULT_LLM_PROVIDER=qwen
DEFAULT_LLM_MODEL=qwen-max
```

### 启动成功后

- 服务首页：http://localhost:8000
- API 文档（Swagger UI）：http://localhost:8000/docs
- 在 Swagger UI 中可以直接测试所有接口

## 🏗️ 项目架构

```
新闻抓取AI分析/
├── news_collector/          # 新闻采集模块
│   ├── collectors/          # 各媒体采集器
│   ├── deduplicator.py     # 新闻去重器
│   └── scheduler.py        # 定时调度器
├── ai_analyst/             # AI 分析引擎
│   ├── prompts/            # Prompt 模板
│   ├── llm_client.py       # LLM 客户端封装
│   ├── analyzer.py         # 核心分析逻辑
│   └── rating_system.py    # 评级系统
├── visualizer/             # 可视化模块
│   ├── generator.py        # 图片生成器
│   ├── templates/          # 图片模板
│   └── assets/             # 字体、图标资源
├── api/                    # API 服务
│   ├── main.py             # FastAPI 入口
│   ├── routes/             # 路由
│   └── schemas.py          # 请求/响应模型
├── database/               # 数据存储
│   ├── models.py           # 数据库模型
│   └── crud.py             # 数据操作
├── tests/                  # 单元测试
├── scripts/                # 辅助脚本
├── start.bat               # Windows 一键启动
├── start.sh                # Linux/macOS 一键启动
├── requirements.txt         # Python 依赖
├── config.example.yaml     # 配置文件模板
└── .env.example            # 环境变量模板
```

## 🛠️ 技术栈

| 层级 | 技术选型 |
|------|-----------|
| 核心语言 | Python 3.10+ |
| LLM 接口 | OpenAI API / Anthropic API / 通义千问 / 文心一言 |
| 新闻抓取 | requests + BeautifulSoup4 |
| 图片生成 | Pillow + matplotlib |
| Web 框架 | FastAPI |
| 数据库 | SQLAlchemy ORM + SQLite/PostgreSQL |
| 配置管理 | pydantic-settings |
| 日志系统 | Loguru |

## 📅 开发路线图

### ✅ 第一阶段（MVP）
- [x] 项目架构设计
- [x] 基于 LLM 的核心分析引擎
- [x] 基础图片生成功能（亮色/暗色主题）
- [x] REST API 服务 + Swagger UI
- [x] 一键启动脚本
- [ ] 3-5 个主流新闻源采集器

### 🔜 第二阶段（功能完善）
- [ ] 更多新闻源接入（10+）
- [ ] 定时自动分析任务
- [ ] Telegram / 微信机器人推送

### 🔮 第三阶段（高级功能）
- [ ] Web 管理后台
- [ ] 分析效果回溯与评估
- [ ] 历史数据分析优化模型

## ⚠️ 免责声明

本工具仅供学习研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

## 📄 开源协议

本项目采用 **MIT License** —— 自由使用、修改、分发。

---

<p align="center">
  ⭐ 如果这个项目对你有帮助，请给它一个 Star！
</p>

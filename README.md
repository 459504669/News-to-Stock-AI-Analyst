# News-to-Stock AI Analyst 📰📈

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

## 🏗️ 项目架构

```
News-to-Stock-AI-Analyst/
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
└── scripts/                # 辅助脚本
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 运行分析（CLI 模式）

```bash
python scripts/test_analysis.py
```

### 5. 启动 API 服务

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

## 📊 输出示例

每一次分析会生成一张 **1200×1600 像素纵向长图**，包含：

| 区域 | 内容 |
|------|------|
| 📰 标题区 | 新闻标题、来源、发布时间 |
| ⚡ 影响评级 | 仪表盘式 1-5 星评分 |
| 📊 详细分析 | 300-500 字 AI 深度解读 |
| 🎯 投资方向 | 受益板块、关注标的、配置建议 |
| ⚠️ 风险提示 | 可能的负面因素 |
| 📱 页脚 | 项目 Logo + 生成时间 |

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
- [ ] 3-5 个主流新闻源采集器
- [ ] 基于 GPT-4 的核心分析引擎
- [ ] 基础图片生成功能
- [ ] CLI 单条新闻分析命令

### 🔜 第二阶段（功能完善）
- [ ] 更多新闻源接入（10+）
- [ ] 多 LLM 后端支持
- [ ] REST API 服务
- [ ] 定时自动分析任务

### 🔮 第三阶段（高级功能）
- [ ] Web 管理后台
- [ ] Telegram / Discord 机器人推送
- [ ] 分析效果回溯与评估
- [ ] 历史数据分析优化模型

## ⚙️ 配置说明

编辑 `config.yaml` 自定义：

```yaml
llm:
  provider: "openai"          # openai / anthropic / qwen / wenxin
  model: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"

news:
  sources:
    - "cailianshe"
    - "sina_finance"
    - "reuters"
  fetch_interval: 300          # 秒

visualizer:
  theme: "light"               # light / dark
  width: 1200
  height: 1600
```

## 🤝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 开源协议

本项目采用 **MIT License** —— 自由使用、修改、分发。

## ⚠️ 免责声明

本工具仅供学习研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

## 🙏 致谢

- OpenAI / Anthropic / 阿里云 / 百度智能云 提供 LLM 能力
- 各财经媒体提供新闻数据源

---

<p align="center">
  ⭐ 如果这个项目对你有帮助，请给它一个 Star！
</p>

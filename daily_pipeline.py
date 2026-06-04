"""
自动化流程 - 启动后自动抓取→分析→生成市场日报图
核心入口脚本，由 run.bat 或 uvicorn lifespan 调用
"""
import sys
import os
import time
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from loguru import logger

# 确保项目根目录在 path 中
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 配置日志
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from news_collector.collectors.collectors import get_all_collectors
from news_collector.deduplicator import deduplicate
from ai_analyst.batch_analyzer import BatchAnalyzer
from visualizer.market_daily import MarketDailyVisualizer


def _fetch_one(collector) -> list:
    """单个采集器的抓取任务（用于线程池）"""
    try:
        items = collector.fetch()
        return items
    except Exception as e:
        logger.warning(f"采集器 {collector.SOURCE_NAME} 失败: {e}")
        return []


def _show_config_hint(error_msg: str = ""):
    """当 API 配置出错时，打印配置修复提示"""
    logger.error("")
    logger.error("=" * 60)
    logger.error("  API 配置错误！请检查 .env 文件")
    logger.error("=" * 60)
    if error_msg:
        logger.error(f"  错误详情: {error_msg}")
    logger.error("")
    logger.error("  常见修复方案:")
    logger.error("  1. 通义千问 (推荐):")
    logger.error("     QWEN_API_KEY=sk-xxxxxx")
    logger.error("     DEFAULT_LLM_PROVIDER=qwen")
    logger.error("     DEFAULT_LLM_MODEL=qwen-max")
    logger.error("")
    logger.error("  2. OpenAI:")
    logger.error("     OPENAI_API_KEY=sk-xxxxxx")
    logger.error("     DEFAULT_LLM_PROVIDER=openai")
    logger.error("     DEFAULT_LLM_MODEL=gpt-4o")
    logger.error("")
    logger.error("  3. 其他模型:")
    logger.error("     qwen:  qwen-max / qwen-plus / qwen-turbo")
    logger.error("     openai: gpt-4o / gpt-4o-mini / gpt-3.5-turbo")
    logger.error("=" * 60)
    logger.error("")
    logger.error("  修改方法: 关闭此窗口，在项目目录下打开 .env 文件修改")
    logger.error("           然后重新双击 start.vbs 启动")
    logger.error("")


def run_daily_pipeline(theme: str = "light") -> Path:
    """
    执行完整的每日分析流程：
    1. 从多个新闻源并发抓取最新新闻
    2. 去重
    3. 批量 AI 分析
    4. 生成市场日报图

    返回生成的图片路径
    """
    logger.info("=" * 60)
    logger.info("开始每日分析流程")
    logger.info("=" * 60)

    # Step 1: 分域名分组并发抓取新闻（避免同一域名高频请求触发反爬）
    logger.info("[1/4] 正在从各新闻源并发抓取新闻...")
    collectors = get_all_collectors()
    all_news = []

    # 按域名分组（同域名的采集器串行，间隔1-2秒；不同域名可并发）
    domain_groups = defaultdict(list)
    for c in collectors:
        url = getattr(c, "URL", "") or ""
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path or "unknown"
        # 提取主域名（去掉 www. 和多余子域名）
        parts = domain.split(".")
        if len(parts) >= 2:
            # 如 www.sina.com.cn → sina.com.cn, people.com.cn → people.com.cn
            if len(parts) >= 3 and parts[0] == "www":
                main_domain = ".".join(parts[1:])
            else:
                main_domain = ".".join(parts[-2:]) if len(parts) >= 2 else domain
        else:
            main_domain = domain
        domain_groups[main_domain].append(c)

    logger.info(f"  共 {len(collectors)} 个采集器，分 {len(domain_groups)} 个域名组")

    for idx, (domain, group_collectors) in enumerate(domain_groups.items()):
        group_name = domain if len(domain) < 30 else domain[:27] + "..."
        logger.info(f"  [{group_name}] {len(group_collectors)} 个采集器...")

        # 同域名组内：如果有多个采集器，顺序执行并加间隔
        if len(group_collectors) > 1:
            for i, c in enumerate(group_collectors):
                try:
                    items = _fetch_one(c)
                    all_news.extend(items)
                    logger.info(f"    {c.SOURCE_NAME}: +{len(items)} 条")
                except Exception as e:
                    logger.warning(f"    {c.SOURCE_NAME}: {e}")
                # 同域名下一个请求前随机等待 0.8-1.5 秒
                if i < len(group_collectors) - 1:
                    time.sleep(0.8 + random.random() * 0.7)
        else:
            # 单个采集器直接执行
            c = group_collectors[0]
            try:
                items = _fetch_one(c)
                all_news.extend(items)
                logger.info(f"    {c.SOURCE_NAME}: +{len(items)} 条")
            except Exception as e:
                logger.warning(f"    {c.SOURCE_NAME}: {e}")

        # 不同域名组之间随机间隔 0.3-0.8 秒（最后一个组不加）
        if idx < len(domain_groups) - 1:
            time.sleep(0.3 + random.random() * 0.5)

    logger.info(f"原始抓取: {len(all_news)} 条")

    if not all_news:
        logger.error("没有抓取到任何新闻！请检查网络连接。")
        return None

    # Step 2: 去重
    logger.info("[2/4] 正在去重...")
    unique_news = deduplicate(all_news, threshold=0.85)
    logger.info(f"去重后: {len(unique_news)} 条")

    # Step 3: AI 分析
    logger.info("[3/4] 正在调用 AI 进行综合分析（可能需要 30-60 秒）...")
    provider = os.getenv("DEFAULT_LLM_PROVIDER", "qwen")
    model = os.getenv("DEFAULT_LLM_MODEL", "qwen-max")

    # 如果模型是 auto 或其他无效值，给出提示
    if model.lower() == "auto" or not model or model == "your_model_name_here":
        _show_config_hint(f"模型名 '{model}' 无效")
        return None

    analyzer = BatchAnalyzer(llm_provider=provider, llm_model=model)

    try:
        result = analyzer.analyze(unique_news)
    except Exception as e:
        error_str = str(e).lower()
        # 捕获常见的 API 配置错误
        if "model_not_found" in error_str or "does not exist" in error_str:
            _show_config_hint(f"模型 '{model}' 不存在，请检查 DEFAULT_LLM_MODEL 配置")
        elif "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
            _show_config_hint("API Key 无效或过期，请检查对应提供商的 API Key")
        elif "insufficient_quota" in error_str or "quota" in error_str:
            _show_config_hint("API 额度已用完，请充值或更换 Key")
        else:
            logger.error(f"AI 分析失败: {e}")
        return None

    if not result:
        logger.error("AI 分析返回空结果，请检查 API 配置。")
        return None

    logger.info(f"分析完成: 评级={result.overall_rating} (置信度={result.confidence:.0%})")

    # Step 4: 生成日报图
    logger.info("[4/4] 正在生成市场日报图...")
    visualizer = MarketDailyVisualizer(theme=theme)
    output_path = visualizer.generate(result)

    logger.info("=" * 60)
    logger.info(f"市场日报图已生成: {output_path}")
    logger.info("=" * 60)

    return output_path


if __name__ == "__main__":
    # 命令行直接运行
    theme = "light"
    if "--dark" in sys.argv:
        theme = "dark"

    print("\n" + "=" * 50)
    print("  News-to-Stock AI Analyst - 市场日报")
    print("=" * 50 + "\n")

    result_path = run_daily_pipeline(theme=theme)

    if result_path:
        print(f"\n日报图生成成功: {result_path}")
        print("打开浏览器访问 http://localhost:8000/api/daily-report 查看最新日报\n")
    else:
        print("\n日报生成失败，请检查日志\n")

    sys.exit(0 if result_path else 1)

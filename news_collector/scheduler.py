"""
新闻采集调度器 - 定时抓取新闻
支持定时任务和手动触发
"""
import schedule
import time
from loguru import logger
from typing import Optional


class NewsScheduler:
    """新闻采集调度器"""

    def __init__(self, collectors: list, interval_minutes: int = 5):
        """
        Args:
            collectors: 采集器实例列表
            interval_minutes: 采集间隔（分钟）
        """
        self.collectors = collectors
        self.interval = interval_minutes
        self._running = False

    def _collect_all(self):
        """执行一轮采集"""
        from .deduplicator import deduplicate

        all_news = []
        for collector in self.collectors:
            try:
                items = collector.fetch()
                all_news.extend(items)
                logger.info(f"{collector.__class__.__name__}: 抓取 {len(items)} 条")
            except Exception as e:
                logger.error(f"{collector.__class__.__name__} 采集失败: {e}")

        # 去重
        unique = deduplicate(all_news)
        logger.info(f"本轮采集完成：共 {len(unique)} 条不重复新闻")
        return unique

    def start(self):
        """启动定时调度"""
        self._running = True
        logger.info(f"调度器启动，每 {self.interval} 分钟采集一次")

        schedule.every(self.interval).minutes.do(self._collect_all)

        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        """停止调度"""
        self._running = False
        logger.info("调度器已停止")

    def collect_once(self):
        """手动触发一次采集"""
        return self._collect_all()

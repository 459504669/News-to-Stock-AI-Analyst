"""
财联社新闻采集器
RSS: https://www.cls.cn/telegraph
"""
import feedparser
from datetime import datetime
from loguru import logger
from .base import BaseCollector, NewsItem


class CailiansheCollector(BaseCollector):
    """财联社电报采集器"""

    RSS_URL = "https://www.cls.cn/telegraph"

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.RSS_URL)
            items = []
            for entry in feed.entries[:20]:
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "")[:200],
                    content=entry.get("summary", ""),
                    source="财联社",
                    url=entry.get("link", ""),
                    published_at=published,
                ))
            logger.info(f"财联社抓取完成，共 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"财联社抓取失败: {e}")
            return []


class SinaFinanceCollector(BaseCollector):
    """新浪财经新闻采集器"""

    RSS_URL = "https://rss.sina.com.cn/finance/forex.xml"

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.RSS_URL)
            items = []
            for entry in feed.entries[:20]:
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "")[:200],
                    content=entry.get("summary", ""),
                    source="新浪财经",
                    url=entry.get("link", ""),
                    published_at=published,
                ))
            logger.info(f"新浪财经抓取完成，共 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"新浪财经抓取失败: {e}")
            return []


class EastmoneyCollector(BaseCollector):
    """东方财富新闻采集器"""

    RSS_URL = "https://feed.eastmoney.com/news/cat_1.xml"

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.RSS_URL)
            items = []
            for entry in feed.entries[:20]:
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "")[:200],
                    content=entry.get("summary", ""),
                    source="东方财富",
                    url=entry.get("link", ""),
                    published_at=published,
                ))
            logger.info(f"东方财富抓取完成，共 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"东方财富抓取失败: {e}")
            return []


class ReutersCollector(BaseCollector):
    """路透社新闻采集器"""

    RSS_URL = "https://feeds.reuters.com/reuters/businessNews"

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.RSS_URL)
            items = []
            for entry in feed.entries[:20]:
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "")[:200],
                    content=entry.get("summary", ""),
                    source="路透社",
                    url=entry.get("link", ""),
                    published_at=published,
                ))
            logger.info(f"路透社抓取完成，共 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"路透社抓取失败: {e}")
            return []


class BloombergCollector(BaseCollector):
    """彭博社新闻采集器（通过 RSS）"""

    RSS_URL = "https://www.bloomberg.com/feed/podcast/etf-iq.xml"

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.RSS_URL)
            items = []
            for entry in feed.entries[:10]:
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "")[:200],
                    content=entry.get("summary", ""),
                    source="彭博社",
                    url=entry.get("link", ""),
                    published_at=published,
                ))
            logger.info(f"彭博社抓取完成，共 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"彭博社抓取失败: {e}")
            return []

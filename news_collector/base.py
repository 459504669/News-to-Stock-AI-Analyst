"""
基础新闻采集器 - 所有采集器的抽象基类
"""
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from loguru import logger


@dataclass
class NewsItem:
    """新闻数据模型"""
    title: str
    summary: str
    content: str
    source: str
    url: str
    published_at: datetime
    image_url: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, NewsItem):
            return False
        return self.url == other.url or self.title == other.title

    def __hash__(self):
        return hash(self.url)


class BaseCollector(ABC):
    """采集器抽象基类"""

    def __init__(self, timeout: int = 10, retry_times: int = 3):
        self.timeout = timeout
        self.retry_times = retry_times
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        """抓取新闻，返回 NewsItem 列表"""
        pass

    def _get(self, url: str, **kwargs) -> requests.Response:
        """带重试的 GET 请求"""
        from tenacity import retry, stop_after_attempt, wait_fixed
        @retry(stop=stop_after_attempt(self.retry_times),
               wait=wait_fixed(2))
        def _do_get():
            resp = self.session.get(
                url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        return _do_get()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.session.close()

"""
批量新闻采集器集合 - 纯 requests + BeautifulSoup 版本
直接访问权威新闻网站提取新闻列表，不依赖浏览器自动化

v0.2.5 更新：
  - 新浪财经：换用首页，更新选择器
  - 财联社：换用首页（电报页需JS渲染）
  - 和讯网：换用 news.hexun.com 子站，修复 GBK 编码
  - 华尔街见闻：DNS 可能不通，保留但降优先级
  - 新增 IT之家(ithome.com) 科技新闻源
"""
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from loguru import logger
from bs4 import BeautifulSoup
from ..base import BaseCollector, NewsItem


# ==================== 通用工具 ====================

NAV_BLACKLIST = {
    "首页", "关于", "关于我们", "联系我们", "登录", "注册",
    "搜索", "更多", "下一页", "上一页", "频道", "导航", "订阅",
    "分享", "收藏", "推荐", "热榜", "排行", "排行榜", "点击",
    "评论", "转发", "点赞", "阅读", "home", "about", "contact",
    "login", "register", "search", "more", "next", "previous",
    "nav", "channel", "subscribe", "share", "collect", "top",
    "hot", "rank", "click", "comment", "repost", "like",
    "回到顶部", "返回首页", "意见反馈", "免责声明", "隐私政策",
    "使用条款", "帮助中心", "客户端", "APP下载", "二维码",
    "广告合作", "加入我们", "招聘", "媒体报道", "友情链接",
}

FINANCE_KEYWORDS = [
    "股", "市", "涨", "跌", "A股", "港股", "美股", "指数", "大盘", "板块", "行情",
    "经济", "金融", "银行", "保险", "地产", "科技", "半导体", "芯片", "AI", "人工智能",
    "政策", "央行", "美联储", "加息", "降息", "降准", "货币政策", "财政政策",
    "GDP", "CPI", "PMI", "通胀", "通缩", "通膨", "衰退", "复苏",
    "贸易", "关税", "人民币", "美元", "汇率", "贬值", "升值",
    "原油", "黄金", "期货", "期权", "比特币", "加密货币", "数字货币",
    "财报", "业绩", "营收", "利润", "净利润", "分红", "股息",
    "收购", "并购", "上市", "IPO", "退市", "停牌", "复牌", "增发",
    "中概", "外资", "北向", "南向", "QFII", "北交所", "科创板", "创业板",
    "恒大", "融创", "万科", "碧桂园", "保利", "招商蛇口",
    "阿里", "腾讯", "字节", "美团", "拼多多", "京东", "百度", "小米", "蔚来", "理想", "小鹏",
    "比亚迪", "宁德时代", "隆基", "通威", "海油", "石油", "石化", "能源", "中海油",
    "茅台", "五粮液", "泸州老窖", "汾酒", "洋河", "古井贡",
    "银行", "券商", "保险", "信托", "基金", "公募", "私募", "资管",
    "光伏", "风电", "新能源", "储能", "锂电", "氢能", "电网",
    "消费", "零售", "餐饮", "旅游", "酒店", "航空", "快递", "物流",
    "医药", "医疗", "生物", "疫苗", "创新药", "CXO", "CRO",
    "汽车", "造车", "新能源", "电动", "智能", "自动驾驶",
    "房地产", "楼市", "房价", "土拍", "限购", "房贷利率",
    "债券", "国债", "地方债", "信用债", "收益率", "违约",
    "风险", "危机", "暴雷", "逾期", "重组", "破产", "清算",
    "会议", "公报", "决议", "发布会", "讲话", "表态",
    # 科技/IT 相关（IT之家需要）
    "英伟达", "NVIDIA", "AMD", "英特尔", "Intel", "高通", "台积电", "三星",
    "苹果", "Apple", "华为", "鸿蒙", "麒麟", "iPhone", "iPad", "Mac",
    "特斯拉", "Tesla", "马斯克", "黄仁勋", "库克",
    "机器人", "大模型", "GPT", "ChatGPT", "OpenAI", "Anthropic", "Gemini",
    "鸿蒙智行", "问界", "极氪", "零跑", "小米SU7", "赛力斯",
    "WWDC", "发布", "新品", "旗舰", "处理器", "芯片", "CPU", "GPU",
    "OLED", "折叠屏", "AI手机", "AR", "VR", "MR",
    "自动驾驶", "FSD", "辅助驾驶",
]


def _is_nav_link(title: str, href: str) -> bool:
    """判断是否是导航/广告链接"""
    title_lower = title.lower().strip()
    if len(title_lower) < 2:
        return True
    for kw in NAV_BLACKLIST:
        if kw in title_lower:
            return True
    return False


def _looks_like_news(title: str, href: str) -> bool:
    """判断标题+链接是否像新闻"""
    url_indicators = [
        "news", "article", "detail", "content", "post", "story",
        "2025", "2026", "2024", "roll", "a/", "telegraph",
        "finance", "stock", "company", "economy", "business",
        "html", "htm", "shtml", "php", "jsp", "aspx",
        # IT之家 URL 模式
        "/0/", "ithome.com",
        # 财联社 URL 模式
        "/detail/",
    ]
    has_url_indicator = any(kw in href.lower() for kw in url_indicators)
    has_finance_kw = any(kw in title for kw in FINANCE_KEYWORDS)

    exclude_patterns = [
        r'^\d+$',
        r'^\d{4}-\d{2}-\d{2}$',
        r'^[\d\s\.]+$',
    ]
    for pattern in exclude_patterns:
        if re.match(pattern, title.strip()):
            return False

    return has_url_indicator or has_finance_kw


def _fix_url(href: str, base_url: str) -> str:
    """修复相对链接为绝对链接"""
    if not href or href.startswith("javascript") or href == "#":
        return ""
    if not href.startswith("http"):
        href = urljoin(base_url, href)
    return href


def _safe_parse_html(resp, force_encoding=None) -> BeautifulSoup:
    """安全解析 HTML，自动处理编码"""
    if force_encoding:
        resp.encoding = force_encoding
    else:
        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception:
            resp.encoding = "utf-8"
    text = resp.text
    # 优先 lxml，fallback html.parser
    try:
        return BeautifulSoup(text, "lxml")
    except Exception:
        return BeautifulSoup(text, "html.parser")


# ==================== 通用采集器基类 ====================

class HttpCollector(BaseCollector):
    """
    基于 HTTP 请求的采集器基类
    使用 requests + BeautifulSoup 提取新闻
    """
    URL = ""
    SELECTORS = []
    SOURCE_NAME = ""
    MAX_ITEMS = 15
    REFERER = ""
    FORCE_ENCODING = None  # 强制指定编码

    def fetch(self) -> list[NewsItem]:
        """抓取新闻入口"""
        try:
            items = self._fetch()
            logger.info(f"{self.SOURCE_NAME}: 抓取 {len(items)} 条")
            return items
        except Exception as e:
            logger.warning(f"{self.SOURCE_NAME}: 抓取失败: {e}")
            return []

    def _fetch(self) -> list[NewsItem]:
        """实际抓取逻辑"""
        headers = {}
        if self.REFERER:
            headers["Referer"] = self.REFERER

        resp = self._get(self.URL, headers=headers)
        soup = _safe_parse_html(resp, force_encoding=self.FORCE_ENCODING)

        items = []

        # 1. 尝试硬编码选择器
        for selector in self.SELECTORS:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:self.MAX_ITEMS * 2]:
                    link = elem if elem.name == "a" else elem.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    href = _fix_url(href, self.URL)
                    if title and href and self._validate_item(title, href):
                        items.append(self._create_item(title, href))
                if items:
                    break

        # 2. 通用 fallback
        if not items:
            items = self._generic_extract(soup)

        return items[:self.MAX_ITEMS]

    def _generic_extract(self, soup: BeautifulSoup) -> list[NewsItem]:
        """通用提取：遍历所有链接，智能过滤"""
        items = []
        seen = set()

        for link in soup.find_all("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            href = _fix_url(href, self.URL)

            if not title or not href:
                continue
            if len(title) < 8 or len(title) > 120:
                continue
            if _is_nav_link(title, href):
                continue
            if not _looks_like_news(title, href):
                continue

            key = title[:40]
            if key in seen:
                continue
            seen.add(key)

            items.append(self._create_item(title, href))

            if len(items) >= self.MAX_ITEMS:
                break

        return items

    def _validate_item(self, title: str, href: str) -> bool:
        """验证单条新闻是否有效"""
        if not title or not href:
            return False
        if len(title) < 8 or len(title) > 120:
            return False
        if _is_nav_link(title, href):
            return False
        return True

    def _create_item(self, title: str, href: str) -> NewsItem:
        """创建 NewsItem"""
        return NewsItem(
            title=title,
            summary=title[:300],
            content=title,
            source=self.SOURCE_NAME,
            url=href,
            published_at=datetime.now(),
        )


# ==================== 具体采集器 ====================

class SinaFinanceCollector(HttpCollector):
    """新浪财经 - 首页要闻"""
    URL = "https://finance.sina.com.cn/"
    SELECTORS = [
        ".feed-card-item a",
        ".m-pic-news a",
        "#live-list a",
        ".news-feed a",
        ".list_009 li a",
        "h2 a",
        "h3 a",
    ]
    SOURCE_NAME = "新浪财经"
    MAX_ITEMS = 20
    REFERER = "https://www.sina.com.cn/"


class EastmoneyCollector(HttpCollector):
    """东方财富 - 财经要闻"""
    URL = "https://finance.eastmoney.com/a/czqyw.html"
    SELECTORS = [
        ".title a",
        ".item a",
        ".news-item a",
        ".text a",
        "h3 a",
        ".article-list a",
        ".list-item a",
    ]
    SOURCE_NAME = "东方财富"
    MAX_ITEMS = 20
    REFERER = "https://finance.eastmoney.com/"


class HexunCollector(HttpCollector):
    """和讯网 - 新闻频道"""
    URL = "https://news.hexun.com/"
    SELECTORS = [
        "li a[href*='.html']",
        ".news-item a",
        ".item a",
        ".title a",
        "h3 a",
        "h2 a",
        ".list-item a",
    ]
    SOURCE_NAME = "和讯网"
    MAX_ITEMS = 20
    REFERER = "https://www.hexun.com/"
    FORCE_ENCODING = "gbk"  # 和讯网使用 GBK 编码


class YicaiCollector(HttpCollector):
    """第一财经"""
    URL = "https://www.yicai.com/"
    SELECTORS = [
        ".m-list a",
        ".f-ff1 a",
        ".news-list a",
        ".item a",
        "h2 a",
        "h3 a",
        ".txt a",
        ".list-item a",
    ]
    SOURCE_NAME = "第一财经"
    MAX_ITEMS = 15
    REFERER = "https://www.yicai.com/"


class STCNCollector(HttpCollector):
    """证券时报"""
    URL = "https://www.stcn.com/"
    SELECTORS = [
        ".news-item a",
        ".item a",
        ".title a",
        ".list a",
        "h3 a",
        "h2 a",
        ".con a",
        ".list-item a",
    ]
    SOURCE_NAME = "证券时报"
    MAX_ITEMS = 15
    REFERER = "https://www.stcn.com/"


class CailiansheCollector(HttpCollector):
    """财联社 - 首页要闻（电报页需要JS渲染，改用首页）"""
    URL = "https://www.cls.cn/"
    SELECTORS = [
        "a[href*='/detail/']",
        ".telegraph-content a",
        ".content a",
        "h3 a",
        "h2 a",
        ".news-item a",
        ".item a",
    ]
    SOURCE_NAME = "财联社"
    MAX_ITEMS = 20
    REFERER = "https://www.cls.cn/"


class WallstreetcnCollector(HttpCollector):
    """华尔街见闻（DNS 可能不通，保留备用）"""
    URL = "https://wallstreetcn.com/news/global"
    SELECTORS = [
        ".article-item a",
        ".news-item a",
        ".item a",
        "h2 a",
        "h3 a",
        ".article-card a",
        ".list-item a",
    ]
    SOURCE_NAME = "华尔街见闻"
    MAX_ITEMS = 15
    REFERER = "https://wallstreetcn.com/"


class Kr36Collector(HttpCollector):
    """36氪 - 快讯"""
    URL = "https://36kr.com/newsflashes"
    SELECTORS = [
        ".news-item a",
        ".item a",
        ".title a",
        "h2 a",
        "h3 a",
        ".article-item a",
        ".newsflash-item a",
    ]
    SOURCE_NAME = "36氪"
    MAX_ITEMS = 15
    REFERER = "https://36kr.com/"


class CaixinCollector(HttpCollector):
    """财新网"""
    URL = "https://china.caixin.com/"
    SELECTORS = [
        ".news-item a",
        ".item a",
        ".title a",
        "h2 a",
        "h3 a",
        ".list a",
        ".con a",
        ".list-item a",
    ]
    SOURCE_NAME = "财新网"
    MAX_ITEMS = 15
    REFERER = "https://china.caixin.com/"


class ITHomeCollector(HttpCollector):
    """IT之家 - 科技数码新闻"""
    URL = "https://www.ithome.com/"
    SELECTORS = [
        "li a[href*='ithome.com/0/']",
        "ul li a[href*='/0/']",
        ".lst li a",
        ".hot-list li a",
        "h3 a",
        "h2 a",
        ".title a",
        ".list a",
    ]
    SOURCE_NAME = "IT之家"
    MAX_ITEMS = 25  # IT之家新闻量大，多抓一些
    REFERER = "https://www.ithome.com/"

    # IT之家首页有大量非新闻的工具/下载链接，需要额外过滤
    EXCLUDE_KEYWORDS = {
        "下载", "镜像", "描述文件", "壁纸", "主题", "字体",
        "插件", "扩展", "驱动", "工具", "教程", "设置",
        "立即下载", "点击下载", "免费下载",
    }

    def _validate_item(self, title: str, href: str) -> bool:
        """重写验证，排除IT之家特有的非新闻链接"""
        if not super()._validate_item(title, href):
            return False
        # 排除站内工具/下载页
        for kw in self.EXCLUDE_KEYWORDS:
            if kw in title:
                return False
        # 排除历史页面（编号小于800的一般是很老的常驻链接）
        href_nums = re.findall(r'/(\d+)/\d+\.htm', href)
        if href_nums and int(href_nums[0]) < 800:
            return False
            return False
        return True


# ==================== 入口函数 ====================

def get_all_collectors() -> list[BaseCollector]:
    """获取所有可用的新闻采集器"""
    return [
        SinaFinanceCollector(),       # 新浪财经
        EastmoneyCollector(),         # 东方财富
        HexunCollector(),             # 和讯网
        YicaiCollector(),             # 第一财经
        STCNCollector(),              # 证券时报
        CailiansheCollector(),         # 财联社
        Kr36Collector(),              # 36氪
        CaixinCollector(),            # 财新网
        ITHomeCollector(),            # IT之家（新增）
        WallstreetcnCollector(),      # 华尔街见闻（可能 DNS 不通，放最后）
    ]

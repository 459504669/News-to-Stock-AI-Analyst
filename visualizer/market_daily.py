"""
市场日报图生成器 - 将批量分析结果渲染为一张综合长图
"""
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from ai_analyst.rating_system import Rating, RatingLevel

# 默认字体路径
DEFAULT_FONT = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
WIDTH = 1200


class MarketDailyVisualizer:
    """市场日报图生成器"""

    def __init__(self, theme: str = "light"):
        self.theme = theme
        self._load_fonts()

    def _load_fonts(self):
        try:
            path = str(DEFAULT_FONT)
            self.font_title = ImageFont.truetype(path, 40)
            self.font_heading = ImageFont.truetype(path, 28)
            self.font_body = ImageFont.truetype(path, 22)
            self.font_small = ImageFont.truetype(path, 18)
            self.font_stars = ImageFont.truetype(path, 44)
            self.font_big_stars = ImageFont.truetype(path, 56)
        except IOError:
            logger.warning("字体文件未找到，使用默认字体")
            self.font_title = ImageFont.load_default()
            self.font_heading = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_stars = ImageFont.load_default()
            self.font_big_stars = ImageFont.load_default()

    def _colors(self):
        if self.theme == "dark":
            return {
                "bg": "#1A1A1A",
                "card": "#2D2D2D",
                "text_primary": "#FFFFFF",
                "text_secondary": "#AAAAAA",
                "accent": "#4FC3F7",
                "border": "#444444",
                "red": "#FF6B6B",
                "green": "#66BB6A",
                "gold": "#FFD54F",
                "header_bg": "#1E3A5F",
            }
        else:
            return {
                "bg": "#F0F2F5",
                "card": "#FFFFFF",
                "text_primary": "#1A1A1A",
                "text_secondary": "#666666",
                "accent": "#1976D2",
                "border": "#E0E0E0",
                "red": "#E53935",
                "green": "#43A047",
                "gold": "#FFA000",
                "header_bg": "#1565C0",
            }

    def _wrap_text(self, text: str, width: int = 36) -> str:
        return textwrap.fill(text, width=width)

    def _draw_card(self, draw, x, y, w, h, colors, radius=12):
        draw.rounded_rectangle(
            [(x, y), (x + w, y + h)],
            radius=radius,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )

    def _get_text_height(self, text, font, max_width):
        lines = self._wrap_text(text, width=max_width).split("\n")
        return len(lines) * (font.size + 8)

    def generate(self, result, output_path: Optional[Path] = None) -> Path:
        """
        生成市场日报长图。
        result: BatchAnalysisResult
        """
        colors = self._colors()
        rating = Rating.build(result.overall_rating)

        # ========== 第一遍：计算总高度 ==========
        sections = []

        # Header
        header_h = 180
        sections.append(("header", header_h))

        # 整体情绪
        sentiment_h = 80
        sections.append(("sentiment", sentiment_h))

        # 综合评级
        rating_h = 130
        sections.append(("rating", rating_h))

        # 重要新闻摘要
        top_news_count = len(result.top_news)
        news_block_h = 60 + top_news_count * 60
        sections.append(("top_news", news_block_h))

        # 综合分析
        analysis_lines = len(self._wrap_text(result.market_summary, 36).split("\n"))
        analysis_h = 60 + analysis_lines * 32
        sections.append(("analysis", analysis_h))

        # 热门板块
        sectors_h = 60 + 40 + max(1, len(result.hot_sectors)) * 40
        sections.append(("sectors", sectors_h))

        # 推荐标的
        stocks_h = 60 + 40 + min(8, len(result.hot_stocks)) * 38
        sections.append(("stocks", stocks_h))

        # 风险提示
        risks_h = 60 + 40 + max(1, len(result.key_risks)) * 36
        sections.append(("risks", risks_h))

        # Footer
        footer_h = 70
        sections.append(("footer", footer_h))

        total_h = sum(h for _, h in sections) + len(sections) * 16

        # ========== 第二遍：绘制 ==========
        img = Image.new("RGB", (WIDTH, total_h), color=colors["bg"])
        draw = ImageDraw.Draw(img)

        y = 0

        # ---- Header ----
        draw.rounded_rectangle(
            [(0, y), (WIDTH, y + header_h)],
            radius=0,
            fill=colors["header_bg"],
        )
        draw.text((40, y + 25), "AI 市场日报", font=self.font_title, fill="#FFFFFF")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((40, y + 80), f"分析时间：{now_str}  |  新闻来源：{result.news_count} 条", font=self.font_body, fill="#CCCCCC")
        draw.text((40, y + 115), "News-to-Stock AI Analyst  |  仅供参考，不构成投资建议", font=self.font_small, fill="#999999")
        y += header_h + 12

        # ---- 整体情绪 ----
        self._draw_card(draw, 30, y, WIDTH - 60, sentiment_h, colors)
        sentiment_color = rating.color
        draw.text((50, y + 15), "市场情绪", font=self.font_heading, fill=colors["text_primary"])
        draw.text((200, y + 20), result.overall_sentiment, font=self.font_body, fill=sentiment_color)
        y += sentiment_h + 12

        # ---- 综合评级 ----
        self._draw_card(draw, 30, y, WIDTH - 60, rating_h, colors)
        draw.text((50, y + 15), "综合评级", font=self.font_heading, fill=colors["text_primary"])
        draw.text((50, y + 55), rating.stars, font=self.font_big_stars, fill=rating.color)
        draw.text((350, y + 70), rating.label, font=self.font_title, fill=rating.color)
        # 置信度
        conf_text = f"置信度: {int(result.confidence * 100)}%  |  {result.time_horizon_label}"
        draw.text((350, y + 110), conf_text, font=self.font_small, fill=colors["text_secondary"])
        y += rating_h + 12

        # ---- 重要新闻摘要 ----
        self._draw_card(draw, 30, y, WIDTH - 60, news_block_h, colors)
        draw.text((50, y + 15), f"重要新闻 Top {min(5, top_news_count)}", font=self.font_heading, fill=colors["text_primary"])
        cy = y + 55
        for i, news in enumerate(result.top_news[:5]):
            # 序号圆点
            draw.ellipse([(50, cy + 4), (62, cy + 16)], fill=colors["accent"])
            draw.text((52, cy + 3), str(i + 1), font=self.font_small, fill="#FFFFFF")
            # 标题（自动换行）
            title_wrapped = self._wrap_text(news.get("title", ""), width=42)
            title_lines = title_wrapped.split("\n")
            draw.text((75, cy), title_lines[0], font=self.font_body, fill=colors["text_primary"])
            cy += 28
            # 点评
            comment = news.get("comment", "")[:60]
            if comment:
                draw.text((90, cy), f"→ {comment}", font=self.font_small, fill=colors["text_secondary"])
                cy += 28
            cy += 8
        y += news_block_h + 12

        # ---- 综合分析 ----
        self._draw_card(draw, 30, y, WIDTH - 60, analysis_h, colors)
        draw.text((50, y + 15), "综合分析", font=self.font_heading, fill=colors["text_primary"])
        wrapped = self._wrap_text(result.market_summary, 36)
        draw.text((50, y + 55), wrapped, font=self.font_body, fill=colors["text_secondary"])
        y += analysis_h + 12

        # ---- 热门板块 ----
        self._draw_card(draw, 30, y, WIDTH - 60, sectors_h, colors)
        draw.text((50, y + 15), "热门受益板块", font=self.font_heading, fill=colors["text_primary"])
        cy = y + 55
        for sector in result.hot_sectors[:5]:
            # 板块标签样式
            tag_text = f"  {sector}  "
            tw = self.font_body.getlength(tag_text) + 16
            draw.rounded_rectangle(
                [(50, cy), (50 + int(tw), cy + 32)],
                radius=6,
                fill=colors["accent"],
            )
            draw.text((58, cy + 4), sector, font=self.font_body, fill="#FFFFFF")
            cy += 40
        y += sectors_h + 12

        # ---- 推荐标的 ----
        self._draw_card(draw, 30, y, WIDTH - 60, stocks_h, colors)
        draw.text((50, y + 15), "推荐关注标的", font=self.font_heading, fill=colors["text_primary"])
        cy = y + 55
        for i, stock in enumerate(result.hot_stocks[:8]):
            code = stock.get("code", "")
            name = stock.get("name", "")
            logic = stock.get("logic", "")[:35]
            # 序号
            draw.text((55, cy), f"{i + 1}.", font=self.font_body, fill=colors["accent"])
            # 股票信息
            draw.text((90, cy), f"{code} {name}", font=self.font_body, fill=colors["text_primary"])
            cy += 26
            # 逻辑
            if logic:
                draw.text((110, cy), f"  {logic}", font=self.font_small, fill=colors["text_secondary"])
                cy += 22
            else:
                cy += 8
        y += stocks_h + 12

        # ---- 风险提示 ----
        self._draw_card(draw, 30, y, WIDTH - 60, risks_h, colors)
        draw.text((50, y + 15), "关键风险提示", font=self.font_heading, fill=colors["red"])
        cy = y + 55
        for risk in result.key_risks[:4]:
            draw.text((55, cy), f"  {risk}", font=self.font_body, fill=colors["text_secondary"])
            cy += 36
        y += risks_h + 12

        # ---- Footer ----
        fy = total_h - 50
        draw.text(
            (40, fy),
            "News-to-Stock AI Analyst  |  由 AI 自动生成，仅供参考，不构成投资建议",
            font=self.font_small,
            fill=colors["text_secondary"],
        )

        # 保存
        if output_path is None:
            output_path = Path("output") / "images" / f"daily_report_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, quality=95)
        logger.info(f"市场日报图已生成：{output_path}")
        return output_path

"""
可视化模块 - 生成分析长图（1200×1600）
支持亮色/暗色主题，中英文双语
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap
from loguru import logger
from ..ai_analyst.rating_system import Rating


# 默认字体路径（需用户自行放入字体文件）
DEFAULT_FONT_ZH = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
DEFAULT_FONT_EN = Path(__file__).parent / "assets" / "fonts" / "Inter-Regular.ttf"

# 图片尺寸
WIDTH = 1200
HEIGHT = 1600


class Visualizer:
    """分析图生成器"""

    def __init__(
        self,
        theme: str = "light",
        width: int = WIDTH,
        height: int = HEIGHT,
        font_zh: Optional[Path] = None,
        font_en: Optional[Path] = None,
    ):
        self.theme = theme
        self.width = width
        self.height = height
        self.font_zh_path = font_zh or DEFAULT_FONT_ZH
        self.font_en_path = font_en or DEFAULT_FONT_EN
        self._load_fonts()

    def _load_fonts(self):
        try:
            self.font_title = ImageFont.truetype(str(self.font_zh_path), 36)
            self.font_heading = ImageFont.truetype(str(self.font_zh_path), 28)
            self.font_body = ImageFont.truetype(str(self.font_zh_path), 22)
            self.font_small = ImageFont.truetype(str(self.font_zh_path), 18)
            self.font_stars = ImageFont.truetype(str(self.font_zh_path), 40)
        except IOError:
            logger.warning("字体文件未找到，使用默认字体")
            self.font_title = ImageFont.load_default()
            self.font_heading = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_stars = ImageFont.load_default()

    def _colors(self):
        if self.theme == "dark":
            return {
                "bg": "#1A1A1A",
                "card": "#2D2D2D",
                "text_primary": "#FFFFFF",
                "text_secondary": "#AAAAAA",
                "accent": "#4FC3F7",
                "border": "#444444",
            }
        else:
            return {
                "bg": "#F5F5F5",
                "card": "#FFFFFF",
                "text_primary": "#1A1A1A",
                "text_secondary": "#666666",
                "accent": "#1976D2",
                "border": "#E0E0E0",
            }

    def generate(
        self,
        news_title: str,
        news_source: str,
        news_time: str,
        rating_score: int,
        analysis_summary: str,
        beneficiary_sectors: list[str],
        recommended_stocks: list[dict],
        risks: list[str],
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        生成分析长图，返回图片路径。
        """
        colors = self._colors()
        img = Image.new("RGB", (self.width, self.height), color=colors["bg"])
        draw = ImageDraw.Draw(img)

        y = 40  # 当前绘制 Y 坐标

        # 1. 标题区
        y = self._draw_title_block(draw, news_title, news_source, news_time, colors, y)

        # 2. 评级区
        rating = Rating.build(rating_score)
        y = self._draw_rating_block(draw, rating, colors, y)

        # 3. 分析正文区
        y = self._draw_analysis_block(draw, analysis_summary, colors, y)

        # 4. 投资方向推荐区
        y = self._draw_recommendation_block(
            draw, beneficiary_sectors, recommended_stocks, colors, y
        )

        # 5. 风险提示区
        y = self._draw_risk_block(draw, risks, colors, y)

        # 6. 页脚
        self._draw_footer(draw, colors)

        # 保存
        if output_path is None:
            output_path = Path("output") / "images" / "analysis_latest.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, quality=95)
        logger.info(f"分析图已生成：{output_path}")
        return output_path

    # -------- 各区块绘制方法 --------

    def _draw_title_block(self, draw, title, source, time, colors, y):
        # 标题背景卡片
        draw.rounded_rectangle(
            [(40, y), (self.width - 40, y + 140)],
            radius=12,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )
        # 新闻标题（自动换行）
        wrapped_title = textwrap.fill(title, width=26)
        draw.text((60, y + 20), f"📰 {wrapped_title}", font=self.font_title, fill=colors["text_primary"])
        draw.text((60, y + 90), f"{source}  |  {time}", font=self.font_small, fill=colors["text_secondary"])
        return y + 160

    def _draw_rating_block(self, draw, rating, colors, y):
        draw.rounded_rectangle(
            [(40, y), (self.width - 40, y + 100)],
            radius=12,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )
        draw.text((60, y + 20), "⚡ 市场影响评级", font=self.font_heading, fill=colors["text_primary"])
        draw.text((60, y + 55), rating.stars, font=self.font_stars, fill=rating.color)
        draw.text((300, y + 65), rating.label, font=self.font_heading, fill=rating.color)
        return y + 120

    def _draw_analysis_block(self, draw, summary, colors, y):
        # 自动换行分析文本
        wrapped = textwrap.fill(summary, width=36)
        lines = wrapped.count("\n") + 1
        block_h = 40 + lines * 30 + 20
        draw.rounded_rectangle(
            [(40, y), (self.width - 40, y + block_h)],
            radius=12,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )
        draw.text((60, y + 20), "📊 详细分析解读", font=self.font_heading, fill=colors["text_primary"])
        draw.text((60, y + 55), wrapped, font=self.font_body, fill=colors["text_secondary"])
        return y + block_h + 20

    def _draw_recommendation_block(self, draw, sectors, stocks, colors, y):
        block_h = 40 + len(sectors) * 30 + len(stocks) * 35 + 60
        draw.rounded_rectangle(
            [(40, y), (self.width - 40, y + block_h)],
            radius=12,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )
        cy = y + 20
        draw.text((60, cy), "🎯 投资方向推荐", font=self.font_heading, fill=colors["text_primary"])
        cy += 40
        draw.text((60, cy), f"■ 受益板块：{', '.join(sectors)}", font=self.font_body, fill=colors["text_primary"])
        cy += 30
        for stock in stocks[:5]:
            code = stock.get("code", "")
            name = stock.get("name", "")
            logic = stock.get("logic", "")[:30]
            draw.text((80, cy), f"• {code} {name}：{logic}", font=self.font_small, fill=colors["text_secondary"])
            cy += 35
        return y + block_h + 20

    def _draw_risk_block(self, draw, risks, colors, y):
        block_h = 40 + len(risks) * 30 + 20
        draw.rounded_rectangle(
            [(40, y), (self.width - 40, y + block_h)],
            radius=12,
            fill=colors["card"],
            outline=colors["border"],
            width=1,
        )
        cy = y + 20
        draw.text((60, cy), "⚠️ 风险与不确定性", font=self.font_heading, fill=colors["text_primary"])
        cy += 40
        for risk in risks:
            wrapped = textwrap.fill(f"• {risk}", width=40)
            draw.text((60, cy), wrapped, font=self.font_body, fill=colors["text_secondary"])
            cy += 30
        return y + block_h + 20

    def _draw_footer(self, draw, colors):
        y = self.height - 60
        draw.text(
            (40, y),
            "📱 News-to-Stock AI Analyst  |  由 AI 生成，仅供参考",
            font=self.font_small,
            fill=colors["text_secondary"],
        )

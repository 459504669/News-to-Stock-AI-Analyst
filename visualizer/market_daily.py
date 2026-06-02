"""
市场日报图生成器 v3.0 - 金融终端暗黑 Neon 风格
参考：深蓝黑底 + 青色描边卡片 + 橙红渐变进度条 + 霓虹字效
"""
import textwrap
import math
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from loguru import logger
from ai_analyst.rating_system import Rating, RatingLevel

# 字体路径
DEFAULT_FONT      = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
DEFAULT_FONT_BOLD = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Bold.ttf"

WIDTH = 1080   # 手机竖屏宽度
PAD   = 28     # 全局边距
CARD_PAD = 20  # 卡片内边距

# ── 金融终端暗黑配色 ─────────────────────────────────────────────────────────
#
#  主背景：深蓝黑  #090E1A
#  卡片背景：深蓝  #0D1526
#  青色 neon 描边：#00E5FF / #00BCD4
#  橙色强调（涨）：#FF6D00 / #FF9100
#  红色（利好）：  #FF1744
#  绿色（利空）：  #00E676
#  金色区块标题：  #FFD600
#  文字主色：      #E0F7FA
#  文字次色：      #4DD0E1
#  文字弱色：      #1A3A5C
#

THEME = {
    # 背景层
    "bg":              "#090E1A",
    "bg2":             "#0A1220",
    "surface":         "#0D1526",
    "surface2":        "#101C30",
    "surface3":        "#0B1622",

    # 边框/描边
    "border_cyan":     "#00BCD4",
    "border_cyan_dim": "#005F73",
    "border_gold":     "#FFD600",
    "border_orange":   "#FF6D00",
    "border_red":      "#FF1744",
    "border_green":    "#00E676",

    # 文字
    "text_bright":     "#E0F7FA",
    "text_cyan":       "#4DD0E1",
    "text_gold":       "#FFD600",
    "text_orange":     "#FF9100",
    "text_white":      "#FFFFFF",
    "text_dim":        "#1E4060",
    "text_muted":      "#2A5070",

    # 评级色（A股：红=涨/利好，绿=跌/利空）
    "rating_5":        "#FF1744",   # 强烈利好
    "rating_4":        "#FF5252",   # 利好
    "rating_3":        "#78909C",   # 中性
    "rating_2":        "#00E676",   # 利空
    "rating_1":        "#00C853",   # 强烈利空

    # 特殊元素
    "bull":            "#FF1744",
    "bear":            "#00E676",
    "neutral":         "#78909C",
    "scan_line":       "#FFFFFF05",  # 扫描线（极淡）

    # 渐变进度条颜色
    "bar_track":       "#0D1E30",
    "bar_bull":        "#FF3D00",    # 橙红起点
    "bar_bull_end":    "#FF9100",    # 橙黄终点
    "bar_bear":        "#00BFA5",    # 绿色
    "bar_neutral":     "#37474F",

    # 头部渐变
    "header_top":      "#050A14",
    "header_bot":      "#091530",
    "header_accent":   "#00E5FF",

    # 警示
    "warning_bg":      "#100A00",
    "warning_border":  "#FF6D00",
    "warning_text":    "#FF9100",
}


def _rating_color(score: int) -> str:
    return THEME.get(f"rating_{score}", THEME["neutral"])


# ── 字体工厂 ──────────────────────────────────────────────────────────────────

class FontSet:
    def __init__(self, reg_path: str, bold_path: str = None):
        import os
        # 如果没有 bold 字体或文件不存在，用 Regular 代替
        bp = bold_path if (bold_path and os.path.exists(bold_path)) else reg_path
        try:
            def r(s): return ImageFont.truetype(reg_path, s)
            def b(s): return ImageFont.truetype(bp, s)
            self.hero        = b(52)
            self.h1          = b(30)
            self.h2          = b(24)
            self.h3          = r(21)
            self.body        = r(20)
            self.body_sm     = r(17)
            self.caption     = r(15)
            self.tag         = r(17)
            self.score_big   = b(68)
            self.score_mid   = b(40)
            self.label       = b(18)
            self.ok = True
        except IOError:
            logger.warning("字体加载失败，使用系统默认字体")
            d = ImageFont.load_default()
            for attr in ("hero","h1","h2","h3","body","body_sm","caption","tag",
                         "score_big","score_mid","label"):
                setattr(self, attr, d)
            self.ok = False


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _hex2rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex2rgba(h: str, a: int = 255) -> Tuple[int, int, int, int]:
    r, g, b = _hex2rgb(h)
    return r, g, b, a


def _lerp_color(c1: str, c2: str, t: float) -> Tuple[int, int, int]:
    r1, g1, b1 = _hex2rgb(c1)
    r2, g2, b2 = _hex2rgb(c2)
    return (
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def _wrap(text: str, chars: int = 28) -> str:
    return textwrap.fill(text, width=chars, break_long_words=True)


def _text_wh(draw: ImageDraw.Draw, text: str, font) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _multiline_h(draw: ImageDraw.Draw, text: str, font, gap: int = 6) -> int:
    total = 0
    for line in text.split("\n"):
        _, lh = _text_wh(draw, line, font)
        total += lh + gap
    return max(total, 0)


# ── 扫描线纹理 ────────────────────────────────────────────────────────────────

def _draw_scanlines(img: Image.Image, step: int = 4, alpha: int = 8) -> Image.Image:
    """给画布叠加扫描线，增强终端感"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(0, img.height, step):
        od.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))
    img_rgba = img.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


# ── 渐变背景 ─────────────────────────────────────────────────────────────────

def _draw_gradient_rect(draw: ImageDraw.Draw,
                         x: int, y: int, w: int, h: int,
                         c1: str, c2: str, horizontal: bool = True):
    """在 draw 上绘制渐变矩形"""
    steps = w if horizontal else h
    for i in range(steps):
        t = i / max(steps - 1, 1)
        color = _lerp_color(c1, c2, t)
        if horizontal:
            draw.line([(x + i, y), (x + i, y + h)], fill=color)
        else:
            draw.line([(x, y + i), (x + w, y + i)], fill=color)


# ── Neon 卡片 ─────────────────────────────────────────────────────────────────

def _draw_neon_card(draw: ImageDraw.Draw,
                    x: int, y: int, w: int, h: int,
                    border_color: str = "#00BCD4",
                    fill_color: str = "#0D1526",
                    radius: int = 8,
                    border_width: int = 1):
    """深色填充 + neon 描边圆角卡片"""
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=radius,
        fill=fill_color,
        outline=border_color,
        width=border_width,
    )


def _draw_neon_card_with_shadow(img: Image.Image,
                                 x: int, y: int, w: int, h: int,
                                 border_color: str = "#00BCD4",
                                 fill_color: str = "#0D1526",
                                 radius: int = 8) -> Image.Image:
    """带发光模拟阴影的 neon 卡片"""
    # 发光层（模拟 neon glow）
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r, g, b = _hex2rgb(border_color)
    gd.rounded_rectangle([(x - 2, y - 2), (x + w + 2, y + h + 2)],
                          radius=radius + 2, outline=(r, g, b, 60), width=4)
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, glow)
    img = img_rgba.convert("RGB")

    # 实际描边卡片
    d = ImageDraw.Draw(img)
    _draw_neon_card(d, x, y, w, h, border_color, fill_color, radius)
    return img


# ── 区块标题行 ────────────────────────────────────────────────────────────────

def _draw_block_title(draw: ImageDraw.Draw,
                      x: int, y: int,
                      title: str,
                      icon: str,
                      title_color: str,
                      accent_color: str,
                      fonts: FontSet) -> int:
    """
    左侧竖条 + 彩色圆点 + 标题
    返回：标题高度
    """
    bar_h = 22
    draw.rounded_rectangle([(x, y + 3), (x + 3, y + 3 + bar_h)],
                            radius=1, fill=accent_color)
    # 用程序绘制彩色圆点代替 Unicode 图标（避免字体不支持显示为方框）
    dot_r = 5
    dot_cx = x + 18
    dot_cy = y + 12
    draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r),
                  (dot_cx + dot_r, dot_cy + dot_r)],
                 fill=accent_color)
    draw.text((x + 30, y), title, font=fonts.h2, fill=title_color)
    _, th = _text_wh(draw, title, fonts.h2)
    return th + 4


def _draw_neon_divider(draw: ImageDraw.Draw,
                        x: int, y: int, w: int,
                        color: str = "#005F73"):
    draw.line([(x, y), (x + w, y)], fill=color, width=1)


# ── 渐变进度条（横向，橙红=涨） ───────────────────────────────────────────────

def _draw_neon_bar(draw: ImageDraw.Draw,
                   x: int, y: int, w: int, h: int,
                   value: float,
                   c1: str = "#FF3D00",
                   c2: str = "#FF9100",
                   track: str = "#0D1E30",
                   radius: int = 3):
    """渐变填充进度条"""
    # 轨道
    draw.rounded_rectangle([(x, y), (x + w, y + h)],
                            radius=radius, fill=track)
    filled = max(int(w * value), radius * 2 + 2)
    filled = min(filled, w)
    # 渐变填充
    for i in range(filled):
        t = i / max(filled - 1, 1)
        color = _lerp_color(c1, c2, t)
        cx = x + i
        if i == 0:
            # 左圆角
            draw.rounded_rectangle([(x, y), (x + radius * 2, y + h)],
                                    radius=radius, fill=_lerp_color(c1, c2, 0))
        draw.line([(cx, y + 1), (cx, y + h - 1)], fill=color)
    # 高光线（顶部）
    r, g, b = _lerp_color(c1, c2, 0.6)
    draw.line([(x + 2, y + 1), (x + filled - 2, y + 1)],
              fill=(min(r + 80, 255), min(g + 80, 255), min(b + 80, 255)), width=1)


# ── 头部区块 ──────────────────────────────────────────────────────────────────

def _render_header(img: Image.Image, fonts: FontSet, result, rating: Rating) -> Tuple[Image.Image, int]:
    H = 190
    draw = ImageDraw.Draw(img)
    c = THEME

    # 渐变背景
    for py in range(H):
        t = py / H
        color = _lerp_color(c["header_top"], c["header_bot"], t)
        draw.line([(0, py), (WIDTH, py)], fill=color)

    # 底部 neon 线
    draw.line([(0, H - 2), (WIDTH, H - 2)], fill=c["header_accent"], width=2)
    # 顶部细线
    draw.line([(0, 0), (WIDTH, 0)], fill=c["border_cyan_dim"], width=1)

    # 左侧：系统名
    draw.text((PAD, 22), "AI MARKET TERMINAL", font=fonts.h3, fill=c["text_cyan"])
    draw.text((PAD, 52), "市场日报", font=fonts.hero, fill=c["text_white"])

    # 日期 + 新闻数
    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M")
    draw.text((PAD, 116), now_str, font=fonts.body_sm, fill=c["text_cyan"])
    draw.text((PAD, 140), f"基于 {result.news_count} 条新闻分析", font=fonts.caption, fill=c["text_muted"])

    # 右侧：评级胶囊
    rating_color = _rating_color(rating.score)
    score_text = rating.label
    tw, th_score = _text_wh(draw, score_text, fonts.score_mid)
    badge_px, badge_py = 18, 10
    badge_w = tw + badge_px * 2
    badge_h = th_score + badge_py * 2
    badge_x = WIDTH - badge_w - PAD
    badge_y = 28
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=6, fill=THEME["surface"], outline=rating_color, width=1
    )
    draw.text((badge_x + badge_px, badge_y + badge_py), score_text,
              font=fonts.score_mid, fill=rating_color)

    # 星级
    stars = rating.stars
    stw, _ = _text_wh(draw, stars, fonts.h2)
    draw.text((WIDTH - stw - PAD, 96), stars, font=fonts.h2, fill=rating_color)

    # 置信度
    conf = result.confidence
    bar_x = WIDTH - 220 - PAD
    draw.text((bar_x, 130), "置信度", font=fonts.caption, fill=c["text_cyan"])
    conf_text = f"{int(conf * 100)}%"
    ctw, _ = _text_wh(draw, conf_text, fonts.label)
    draw.text((WIDTH - ctw - PAD, 130), conf_text, font=fonts.label, fill=c["text_orange"])

    _draw_neon_bar(draw, bar_x, 152, 220, 8, conf,
                   c1=c["bar_bull"], c2=c["bar_bull_end"])

    return img, H


# ── 情绪横幅 ──────────────────────────────────────────────────────────────────

def _render_sentiment(draw: ImageDraw.Draw, fonts: FontSet, y: int, result, rating: Rating) -> int:
    H = 52
    c = THEME
    rating_color = _rating_color(rating.score)
    r, g, b = _hex2rgb(rating_color)

    # 半透明填充
    draw.rounded_rectangle([(PAD, y), (WIDTH - PAD, y + H)],
                            radius=6, fill=(r, g, b, 30),
                            outline=rating_color, width=1)

    # 箭头 + 文字（程序绘制三角形代替 Unicode）
    sentiment = result.overall_sentiment or rating.label
    arrow_x = PAD + 16
    arrow_y = y + 17
    draw.polygon([(arrow_x, arrow_y - 5), (arrow_x + 8, arrow_y), (arrow_x, arrow_y + 5)],
                 fill=rating_color)
    draw.text((PAD + 32, y + 12), f"市场整体情绪：{sentiment}",
              font=fonts.h3, fill=c["text_bright"])

    # 右侧时间维度
    h_text = result.time_horizon_label
    htw, _ = _text_wh(draw, h_text, fonts.tag)
    hx = WIDTH - htw - PAD - 20
    draw.rounded_rectangle([(hx - 8, y + 10), (hx + htw + 8, y + H - 10)],
                            radius=4, fill=THEME["surface2"], outline=c["border_cyan_dim"])
    draw.text((hx, y + 14), h_text, font=fonts.tag, fill=c["text_cyan"])

    return H + 14


# ── 新闻区块 ──────────────────────────────────────────────────────────────────

def _est_news_h(fonts: FontSet, news_list: list) -> int:
    # 粗估（实际绘制时精确）
    total = 0
    for news in news_list[:5]:
        title_lines = math.ceil(len(news.get("title", "")) / 26) + 1
        total += title_lines * 28 + 30
    return total + 20


def _render_news(img: Image.Image, draw: ImageDraw.Draw,
                  fonts: FontSet, y: int, news_list: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    inner_h = _est_news_h(fonts, news_list)
    card_h = inner_h + 70

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_cyan"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            f"重要新闻 TOP {min(5, len(news_list))}",
                            "◈", c["text_gold"], c["border_gold"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_cyan_dim"])

    cy = y + 14 + th + 22
    for i, news in enumerate(news_list[:5]):
        title   = news.get("title", "")
        comment = news.get("comment", "")[:80]
        source  = news.get("source", "")
        impact  = news.get("impact", 3)    # 1-5 影响力

        # 序号 + 来源行
        num_color = [c["text_muted"], c["border_cyan_dim"],
                     c["text_cyan"], c["text_orange"], c["border_red"]][min(impact - 1, 4)]
        draw.text((PAD + CARD_PAD, cy), f"{i + 1:02d}", font=fonts.label, fill=num_color)
        if source:
            sw2, _ = _text_wh(draw, source, fonts.caption)
            draw.rounded_rectangle(
                [(PAD + CARD_PAD + 34, cy + 2), (PAD + CARD_PAD + 34 + sw2 + 10, cy + 2 + 18)],
                radius=3, fill=c["surface2"], outline=c["border_cyan_dim"]
            )
            draw.text((PAD + CARD_PAD + 39, cy + 3), source,
                      font=fonts.caption, fill=c["text_cyan"])

        cy += 24

        # 标题
        title_w = _wrap(title, chars=28)
        draw.text((PAD + CARD_PAD + 34, cy), title_w, font=fonts.body, fill=c["text_bright"])
        th2 = _multiline_h(draw, title_w, fonts.body, gap=5) + 4
        cy += th2

        # 点评
        if comment:
            cmt_w = _wrap(f"  → {comment}", chars=32)
            draw.text((PAD + CARD_PAD + 34, cy), cmt_w, font=fonts.body_sm, fill=c["text_cyan"])
            cy += _multiline_h(draw, cmt_w, fonts.body_sm, gap=4) + 2

        cy += 10
        if i < len(news_list[:5]) - 1:
            _draw_neon_divider(draw, PAD + CARD_PAD, cy, card_w - CARD_PAD * 2,
                                c["border_cyan_dim"])
            cy += 12

    return img, draw, (cy - y) + 20


# ── 综合分析区块 ──────────────────────────────────────────────────────────────

def _render_analysis(img: Image.Image, draw: ImageDraw.Draw,
                      fonts: FontSet, y: int, text: str) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    wrapped = _wrap(text, chars=32)
    inner_h = _multiline_h(draw, wrapped, fonts.body, gap=9)
    card_h = inner_h + 80

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_cyan"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "AI 综合分析", "◉", c["text_gold"], c["border_gold"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_cyan_dim"])
    draw.text((PAD + CARD_PAD, y + 14 + th + 22), wrapped,
              font=fonts.body, fill=c["text_bright"], spacing=7)
    return img, draw, card_h + 14


# ── 板块区块 ──────────────────────────────────────────────────────────────────

# 板块标签调色板（终端 neon 色组）
_SECTOR_PALETTE = [
    ("#FF1744", "#200009"),   # 红
    ("#FF6D00", "#1A0D00"),   # 深橙
    ("#FFD600", "#1A1400"),   # 金黄
    ("#00E5FF", "#00131A"),   # 青
    ("#00E676", "#00130A"),   # 绿
    ("#D500F9", "#150022"),   # 紫
    ("#FF4081", "#1A001B"),   # 粉红
    ("#40C4FF", "#001A22"),   # 天蓝
]


def _est_sectors_h(sectors: list) -> int:
    if not sectors:
        return 40
    row_count = math.ceil(min(len(sectors), 10) / 4)
    return row_count * 48 + 10


def _render_sectors(img: Image.Image, draw: ImageDraw.Draw,
                     fonts: FontSet, y: int, sectors: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    inner_h = _est_sectors_h(sectors)
    card_h = inner_h + 72

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_cyan"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "热门受益板块", "◆", c["text_gold"], c["border_gold"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_cyan_dim"])

    cx = PAD + CARD_PAD
    cy = y + 14 + th + 20
    max_x = WIDTH - PAD - CARD_PAD

    for i, sector in enumerate(sectors[:10]):
        fg, bg = _SECTOR_PALETTE[i % len(_SECTOR_PALETTE)]
        tw, _ = _text_wh(draw, sector, fonts.tag)
        tag_w = tw + 20
        tag_h = 32

        if cx + tag_w > max_x:
            cx = PAD + CARD_PAD
            cy += tag_h + 10

        draw.rounded_rectangle([(cx, cy), (cx + tag_w, cy + tag_h)],
                                radius=4, fill=bg, outline=fg, width=1)
        draw.text((cx + 10, cy + 7), sector, font=fonts.tag, fill=fg)
        cx += tag_w + 10

    return img, draw, card_h + 14


# ── 推荐标的区块 ──────────────────────────────────────────────────────────────

def _render_stocks(img: Image.Image, draw: ImageDraw.Draw,
                    fonts: FontSet, y: int, stocks: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    stock_list = stocks[:8]
    rows = math.ceil(len(stock_list) / 2)
    sub_h = 88
    card_h = rows * (sub_h + 8) + 80

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_orange"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "推荐关注标的", "▲", c["text_orange"], c["border_orange"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_orange"])

    col_w = (card_w - CARD_PAD * 2 - 8) // 2
    sy0 = y + 14 + th + 20

    for i, stock in enumerate(stock_list):
        col = i % 2
        row = i // 2
        sx = PAD + CARD_PAD + col * (col_w + 8)
        sy = sy0 + row * (sub_h + 8)

        code   = stock.get("code", "")
        name   = stock.get("name", "")
        logic  = stock.get("logic", "")[:36]
        conf   = stock.get("confidence", 0.7)

        # 子卡片
        _draw_neon_card(draw, sx, sy, col_w, sub_h,
                        border_color=c["border_orange"],
                        fill_color=c["surface2"], radius=6, border_width=1)

        # 序号
        draw.text((sx + 8, sy + 8), f"{i + 1:02d}", font=fonts.caption, fill=c["text_orange"])

        # 股票代码 + 名称
        header = f"{code}  {name}" if code else name
        draw.text((sx + 36, sy + 6), header, font=fonts.h3, fill=c["text_white"])

        # 置信度进度条
        bar_w = col_w - 48
        _draw_neon_bar(draw, sx + 36, sy + 35, bar_w, 6, conf,
                       c1=c["bar_bull"], c2=c["bar_bull_end"])
        conf_text = f"{int(conf * 100)}%"
        ctw, _ = _text_wh(draw, conf_text, fonts.caption)
        draw.text((sx + col_w - ctw - 8, sy + 30), conf_text,
                  font=fonts.caption, fill=c["text_orange"])

        # 逻辑摘要
        if logic:
            draw.text((sx + 8, sy + 52), _wrap(logic, chars=19),
                      font=fonts.caption, fill=c["text_cyan"])

    return img, draw, card_h + 14


# ── 风险提示区块 ──────────────────────────────────────────────────────────────

def _est_risks_h(fonts: FontSet, risks: list) -> int:
    total = 0
    for r in risks[:4]:
        lines = math.ceil(len(r) / 28) + 1
        total += lines * 26 + 10
    return total + 20


def _render_risks(img: Image.Image, draw: ImageDraw.Draw,
                   fonts: FontSet, y: int, risks: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    inner_h = _est_risks_h(fonts, risks)
    card_h = inner_h + 72

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["warning_border"])
    draw = ImageDraw.Draw(img)

    # 背景填充（警示橙）
    draw.rounded_rectangle([(PAD, y), (PAD + card_w, y + card_h)],
                            radius=8, fill=c["warning_bg"],
                            outline=c["warning_border"], width=1)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "关键风险提示", "⚠", c["warning_text"], c["warning_border"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["warning_border"])

    cy = y + 14 + th + 22
    for risk in risks[:4]:
        rw = _wrap(f"  ›  {risk}", chars=30)
        draw.text((PAD + CARD_PAD, cy), rw, font=fonts.body,
                  fill=c["warning_text"], spacing=6)
        cy += _multiline_h(draw, rw, fonts.body, gap=6) + 10

    return img, draw, card_h + 14


# ── 页脚 ──────────────────────────────────────────────────────────────────────

def _render_footer(draw: ImageDraw.Draw, fonts: FontSet, y: int):
    c = THEME
    # 双线页脚
    draw.line([(PAD, y + 4), (WIDTH - PAD, y + 4)], fill=c["border_cyan_dim"], width=1)
    draw.line([(PAD, y + 7), (WIDTH - PAD, y + 7)], fill=c["text_dim"], width=1)
    footer = "News-to-Stock AI Analyst  ·  AI 自动生成  ·  仅供参考，不构成投资建议"
    fw, _ = _text_wh(draw, footer, fonts.caption)
    draw.text(((WIDTH - fw) // 2, y + 16), footer, font=fonts.caption, fill=c["text_muted"])


# ── 主类 ──────────────────────────────────────────────────────────────────────

class MarketDailyVisualizer:
    """市场日报图生成器 v3.0 — 金融终端暗黑风格"""

    def __init__(self, theme: str = "dark"):
        # v3.0 只有一套暗黑主题，theme 参数保留兼容性
        self.theme = "dark"
        self.fonts = FontSet(str(DEFAULT_FONT), str(DEFAULT_FONT_BOLD))

    def generate(self, result, output_path: Optional[Path] = None) -> Path:
        fonts  = self.fonts
        rating = Rating.build(result.overall_rating)
        c      = THEME

        # ── 粗估总高度 ──
        header_h    = 190
        sentiment_h = 66
        news_h      = _est_news_h(fonts, result.top_news) + 80
        analysis_h  = _multiline_h(ImageDraw.Draw(Image.new("RGB", (1, 1))),
                                    _wrap(result.market_summary, 32), fonts.body, 9) + 100
        sectors_h   = _est_sectors_h(result.hot_sectors) + 86
        stocks_h    = (math.ceil(min(8, len(result.hot_stocks)) / 2) * 96) + 94
        risks_h     = _est_risks_h(fonts, result.key_risks) + 86
        footer_h    = 50

        total_h = (header_h + sentiment_h + news_h + analysis_h +
                   sectors_h + stocks_h + risks_h + footer_h + PAD * 12)
        total_h = max(total_h, 1800)

        # ── 创建画布 ──
        img = Image.new("RGB", (WIDTH, total_h), color=c["bg"])

        # ── Header ──
        img, y = _render_header(img, fonts, result, rating)
        draw = ImageDraw.Draw(img)
        y += PAD

        # ── 情绪横幅 ──
        dy = _render_sentiment(draw, fonts, y, result, rating)
        y += dy

        # ── 新闻 ──
        img, draw, dy = _render_news(img, draw, fonts, y, result.top_news)
        y += dy + PAD // 2

        # ── 综合分析 ──
        img, draw, dy = _render_analysis(img, draw, fonts, y, result.market_summary)
        y += dy + PAD // 2

        # ── 热门板块 ──
        img, draw, dy = _render_sectors(img, draw, fonts, y, result.hot_sectors)
        y += dy + PAD // 2

        # ── 推荐标的 ──
        img, draw, dy = _render_stocks(img, draw, fonts, y, result.hot_stocks)
        y += dy + PAD // 2

        # ── 风险提示 ──
        img, draw, dy = _render_risks(img, draw, fonts, y, result.key_risks)
        y += dy + PAD

        # ── Footer ──
        draw = ImageDraw.Draw(img)
        _render_footer(draw, fonts, y)
        y += footer_h

        # ── 扫描线纹理（整体叠加） ──
        img = _draw_scanlines(img, step=3, alpha=10)

        # ── 裁剪 ──
        actual_h = y + PAD
        img = img.crop((0, 0, WIDTH, actual_h))

        # ── 保存 ──
        if output_path is None:
            output_path = (Path("output") / "images" /
                           f"daily_report_{datetime.now().strftime('%Y%m%d_%H%M')}.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG", optimize=True)
        logger.info(f"市场日报图已生成：{output_path}  ({WIDTH}×{actual_h})")
        return output_path

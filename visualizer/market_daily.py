"""
市场日报图生成器 v3.1 - 金融终端暗黑 Neon 风格
v3.1: 精确卡片高度 + 独立程序图标 + 修复框线错位
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
    "rating_5":        "#FF1744",
    "rating_4":        "#FF5252",
    "rating_3":        "#78909C",
    "rating_2":        "#00E676",
    "rating_1":        "#00C853",

    # 特殊元素
    "bull":            "#FF1744",
    "bear":            "#00E676",
    "neutral":         "#78909C",
    "scan_line":       "#FFFFFF05",

    # 渐变进度条颜色
    "bar_track":       "#0D1E30",
    "bar_bull":        "#FF3D00",
    "bar_bull_end":    "#FF9100",
    "bar_bear":        "#00BFA5",
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
        bp = bold_path if (bold_path and os.path.exists(bold_path)) else reg_path
        try:
            def r(s): return ImageFont.truetype(reg_path, s)
            def b(s):
                f = ImageFont.truetype(bp, s)
                # 可变字体需要显式设置 wght=700 才能渲染为粗体
                if hasattr(f, "set_variation_by_axes"):
                    try:
                        f.set_variation_by_axes({"wght": 700})
                    except Exception:
                        pass
                return f
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
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r, g, b = _hex2rgb(border_color)
    gd.rounded_rectangle([(x - 2, y - 2), (x + w + 2, y + h + 2)],
                          radius=radius + 2, outline=(r, g, b, 60), width=4)
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, glow)
    img = img_rgba.convert("RGB")
    d = ImageDraw.Draw(img)
    _draw_neon_card(d, x, y, w, h, border_color, fill_color, radius)
    return img


# ── 区块程序图标（按内容类型绘制不同图形） ──────────────────────────────────

def _draw_section_icon(draw: ImageDraw.Draw, cx: int, cy: int,
                       icon_type: str, color: str):
    """
    在 (cx, cy) 中心绘制 18x18 的程序图标。
    icon_type: "news" | "analysis" | "sectors" | "stocks" | "risks"
    """
    if icon_type == "news":
        # 闪电 ⚡ — 两段锯齿多边形
        pts = [
            (cx + 2, cy - 8),   # 顶部
            (cx - 4, cy),       # 左折
            (cx + 1, cy - 1),   # 中间凹
            (cx - 2, cy + 8),   # 底部
            (cx + 4, cy),       # 右折
            (cx - 1, cy + 1),   # 中间凸
        ]
        draw.polygon(pts, fill=color)

    elif icon_type == "analysis":
        # 靶心 ◎ — 三层同心圆
        draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)],
                     outline=color, width=1)
        draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)],
                     outline=color, width=1)
        draw.ellipse([(cx - 1, cy - 1), (cx + 1, cy + 1)], fill=color)

    elif icon_type == "sectors":
        # 火焰 🔥 — 外焰三角 + 内焰
        draw.polygon([(cx, cy - 8), (cx - 6, cy + 3), (cx + 6, cy + 3)],
                     outline=color, width=1)
        draw.polygon([(cx, cy - 3), (cx - 3, cy + 8), (cx + 3, cy + 8)],
                     outline=color, width=1)
        draw.ellipse([(cx - 2, cy + 2), (cx + 2, cy + 7)], fill=color)

    elif icon_type == "stocks":
        # 上升趋势 📈 — 三角箭头 + 竖线
        draw.polygon([(cx, cy - 8), (cx - 7, cy + 1), (cx + 7, cy + 1)],
                     fill=color)
        draw.rectangle([(cx - 1, cy + 1), (cx + 1, cy + 9)], fill=color)

    elif icon_type == "risks":
        # 警告三角 ⚠ — 外三角 + 感叹号
        pts = [(cx, cy - 8), (cx - 8, cy + 6), (cx + 8, cy + 6)]
        draw.polygon(pts, outline=color, width=1)
        draw.line([(cx, cy - 3), (cx, cy + 2)], fill=color, width=2)
        draw.ellipse([(cx - 1, cy + 3), (cx + 1, cy + 5)], fill=color)


# ── 区块标题行 ────────────────────────────────────────────────────────────────

def _draw_block_title(draw: ImageDraw.Draw,
                      x: int, y: int,
                      title: str,
                      icon_type: str,
                      title_color: str,
                      accent_color: str,
                      fonts: FontSet) -> int:
    """
    左侧竖条 + 程序图标 + 标题文字
    icon_type: "news" | "analysis" | "sectors" | "stocks" | "risks"
    返回：标题高度
    """
    bar_h = 22
    draw.rounded_rectangle([(x, y + 3), (x + 3, y + 3 + bar_h)],
                            radius=1, fill=accent_color)
    # 绘制对应区块的程序图标
    icon_cx = x + 18
    icon_cy = y + 13
    _draw_section_icon(draw, icon_cx, icon_cy, icon_type, accent_color)
    draw.text((x + 32, y), title, font=fonts.h2, fill=title_color)
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
    draw.rounded_rectangle([(x, y), (x + w, y + h)],
                            radius=radius, fill=track)
    filled = max(int(w * value), radius * 2 + 2)
    filled = min(filled, w)
    for i in range(filled):
        t = i / max(filled - 1, 1)
        color = _lerp_color(c1, c2, t)
        cx = x + i
        if i == 0:
            draw.rounded_rectangle([(x, y), (x + radius * 2, y + h)],
                                    radius=radius, fill=_lerp_color(c1, c2, 0))
        draw.line([(cx, y + 1), (cx, y + h - 1)], fill=color)
    r, g, b = _lerp_color(c1, c2, 0.6)
    draw.line([(x + 2, y + 1), (x + filled - 2, y + 1)],
              fill=(min(r + 80, 255), min(g + 80, 255), min(b + 80, 255)), width=1)


# ── 头部区块 ──────────────────────────────────────────────────────────────────

def _render_header(img: Image.Image, fonts: FontSet, result, rating: Rating) -> Tuple[Image.Image, int]:
    H = 190
    draw = ImageDraw.Draw(img)
    c = THEME

    for py in range(H):
        t = py / H
        color = _lerp_color(c["header_top"], c["header_bot"], t)
        draw.line([(0, py), (WIDTH, py)], fill=color)

    draw.line([(0, H - 2), (WIDTH, H - 2)], fill=c["header_accent"], width=2)
    draw.line([(0, 0), (WIDTH, 0)], fill=c["border_cyan_dim"], width=1)

    draw.text((PAD, 22), "AI MARKET TERMINAL", font=fonts.h3, fill=c["text_cyan"])
    draw.text((PAD, 52), "市场日报", font=fonts.hero, fill=c["text_white"])

    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M")
    draw.text((PAD, 116), now_str, font=fonts.body_sm, fill=c["text_cyan"])
    draw.text((PAD, 140), f"基于 {result.news_count} 条新闻分析", font=fonts.caption, fill=c["text_muted"])

    # 右侧：评级胶囊（精确居中）
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

    stars = rating.stars
    stw, _ = _text_wh(draw, stars, fonts.h2)
    draw.text((WIDTH - stw - PAD, 96), stars, font=fonts.h2, fill=rating_color)

    conf = result.confidence
    bar_x = WIDTH - 220 - PAD
    draw.text((bar_x, 130), "置信度", font=fonts.caption, fill=c["text_cyan"])
    conf_text = f"{int(conf * 100)}%"
    ctw, _ = _text_wh(draw, conf_text, fonts.label)
    draw.text((WIDTH - ctw - PAD, 130), conf_text, font=fonts.label, fill=c["text_orange"])

    _draw_neon_bar(draw, bar_x, 152, 220, 8, conf,
                   c1=c["bar_bull"], c2=c["bar_bull_end"])

    return img, H


# ── 情绪横幅（动态高度，根据内容自动调整） ────────────────────────────────

def _calc_sentiment_h(draw, fonts, result, rating) -> int:
    """预计算情绪横幅高度（根据文字内容动态调整）"""
    c = THEME
    card_w = WIDTH - PAD * 2
    text_w_max = card_w - 60  # 左侧箭头+间距 + 右侧留白

    sentiment = result.overall_sentiment or ""
    # 前缀 "市场整体情绪：" 约 8 个中文字
    prefix = "市场整体情绪："
    full_text = f"{prefix}{sentiment}" if sentiment else prefix

    # 计算文字行数（动态换行）
    wrapped = _wrap(full_text, chars=34)
    lines = wrapped.split("\n")
    text_lines_h = sum(
        _text_wh(draw, line, fonts.h3)[1] + 4 for line in lines
    )

    # 右侧标签高度
    h_text = result.time_horizon_label or "短期"
    _, tag_h = _text_wh(draw, h_text, fonts.tag)

    content_h = max(text_lines_h, tag_h + 8)
    return content_h + 32  # 上下各 16px padding


def _render_sentiment(draw: ImageDraw.Draw, fonts: FontSet, y: int, result, rating) -> int:
    c = THEME
    rating_color = _rating_color(rating.score)
    r, g, b = _hex2rgb(rating_color)

    # 动态计算高度
    H = _calc_sentiment_h(draw, fonts, result, rating)
    card_w = WIDTH - PAD * 2

    # 绘制背景卡片
    draw.rounded_rectangle([(PAD, y), (WIDTH - PAD, y + H)],
                            radius=6, fill=(r, g, b, 30),
                            outline=rating_color, width=1)

    # 左侧箭头
    arrow_x = PAD + 16
    arrow_y = y + H // 2
    draw.polygon([(arrow_x, arrow_y - 6), (arrow_x + 10, arrow_y), (arrow_x, arrow_y + 6)],
                 fill=rating_color)

    # 情绪文字（自动换行）
    sentiment = result.overall_sentiment or ""
    prefix = "市场整体情绪："
    full_text = f"{prefix}{sentiment}" if sentiment else prefix
    wrapped = _wrap(full_text, chars=34)
    text_y = y + 12
    text_x = PAD + 36
    for line in wrapped.split("\n"):
        draw.text((text_x, text_y), line, font=fonts.h3, fill=c["text_bright"])
        _, lh = _text_wh(draw, line, fonts.h3)
        text_y += lh + 4

    # 右侧时间维度标签（垂直居中）
    h_text = result.time_horizon_label or "短期"
    htw, hth = _text_wh(draw, h_text, fonts.tag)
    hx = WIDTH - htw - PAD - 20
    tag_y = y + (H - hth - 8) // 2
    draw.rounded_rectangle([(hx - 8, tag_y), (hx + htw + 8, tag_y + hth + 8)],
                            radius=4, fill=THEME["surface2"], outline=c["border_cyan_dim"])
    draw.text((hx, tag_y + 4), h_text, font=fonts.tag, fill=c["text_cyan"])

    return H + 14


# ── 新闻区块（精确高度计算） ────────────────────────────────────────────────

def _calc_news_h(draw, fonts, news_list) -> int:
    """精确预计算新闻区块内容高度（与渲染逻辑完全一致）"""
    display_count = min(10, len(news_list))
    # 标题高度
    _, title_th = _text_wh(draw, f"重要新闻 TOP {display_count}", fonts.h2)
    th = title_th + 4
    total = 14 + th + 22  # top_pad + title + divider_gap

    for i, news in enumerate(news_list[:display_count]):
        total += 24  # 序号 + 来源行
        title = news.get("title", "")
        news_time = news.get("time", "")
        # 标题行：标题 + 时间（如果有）
        if news_time and title:
            # 留出时间标签的空间，标题部分 chars 减 10
            time_tag = f"  [{news_time}]"
            title_display = title + time_tag
            wrapped = _wrap(title_display, chars=30)
        else:
            wrapped = _wrap(title, chars=28)
        total += _multiline_h(draw, wrapped, fonts.body, gap=5) + 4
        comment = news.get("comment", "")[:80]
        if comment:
            cmt = _wrap(f"  -> {comment}", chars=32)
            total += _multiline_h(draw, cmt, fonts.body_sm, gap=4) + 2
        total += 10
        if i < display_count - 1:
            total += 12

    return total + 20  # bottom_pad


def _render_news(img: Image.Image, draw: ImageDraw.Draw,
                  fonts: FontSet, y: int, news_list: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    display_count = min(10, len(news_list))

    # 精确计算卡片高度
    card_h = _calc_news_h(draw, fonts, news_list)

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_cyan"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            f"重要新闻 TOP {display_count}",
                            "news", c["text_gold"], c["border_gold"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_cyan_dim"])

    cy = y + 14 + th + 22
    for i, news in enumerate(news_list[:display_count]):
        title   = news.get("title", "")
        comment = news.get("comment", "")[:80]
        source  = news.get("source", "")
        impact  = news.get("impact", 3)
        news_time = news.get("time", "")

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

        # 标题 + 时间标签（时间用不同颜色）
        if news_time and title:
            title_text = title
            wrapped_title = _wrap(title_text, chars=30)
            tw_lines = wrapped_title.split("\n")
            # 时间标签绘制在标题末尾（第一行或最后行末尾）
            for j, line in enumerate(tw_lines):
                lx = PAD + CARD_PAD + 34
                ly = cy + j * (_text_wh(draw, line, fonts.body)[1] + 5)
                # 最后一行追加时间
                if j == len(tw_lines) - 1:
                    # 绘制标题文字
                    draw.text((lx, ly), line, font=fonts.body, fill=c["text_bright"])
                    lw, _ = _text_wh(draw, line, fonts.body)
                    # 绘制时间标签
                    time_str = f"  [{news_time}]"
                    time_x = lx + lw + 2
                    # 检查是否会超出卡片宽度
                    max_x = WIDTH - PAD - CARD_PAD - 4
                    time_w, _ = _text_wh(draw, time_str, fonts.caption)
                    if time_x + time_w > max_x:
                        # 放到下一行
                        ly2 = ly + _text_wh(draw, line, fonts.body)[1] + 5
                        draw.text((lx, ly2), time_str, font=fonts.caption, fill=c["text_muted"])
                        title_lines_h = (ly2 - cy) + _text_wh(draw, time_str, fonts.caption)[1] + 5
                    else:
                        draw.text((time_x, ly + 3), time_str, font=fonts.caption, fill=c["text_muted"])
                        title_lines_h = _multiline_h(draw, wrapped_title, fonts.body, gap=5) + 4
                else:
                    draw.text((lx, ly), line, font=fonts.body, fill=c["text_bright"])
            th2 = title_lines_h
        else:
            title_w = _wrap(title, chars=28)
            draw.text((PAD + CARD_PAD + 34, cy), title_w, font=fonts.body, fill=c["text_bright"])
            th2 = _multiline_h(draw, title_w, fonts.body, gap=5) + 4
        cy += th2

        if comment:
            cmt_w = _wrap(f"  -> {comment}", chars=32)
            draw.text((PAD + CARD_PAD + 34, cy), cmt_w, font=fonts.body_sm, fill=c["text_cyan"])
            cy += _multiline_h(draw, cmt_w, fonts.body_sm, gap=4) + 2

        cy += 10
        if i < display_count - 1:
            _draw_neon_divider(draw, PAD + CARD_PAD, cy, card_w - CARD_PAD * 2,
                                c["border_cyan_dim"])
            cy += 12

    # 返回实际使用的卡片高度（= card_h）
    return img, draw, card_h + 14


# ── 综合分析区块 ──────────────────────────────────────────────────────────────

def _render_analysis(img: Image.Image, draw: ImageDraw.Draw,
                      fonts: FontSet, y: int, text: str) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    wrapped = _wrap(text, chars=32)
    inner_h = _multiline_h(draw, wrapped, fonts.body, gap=9)
    card_h = 14 + 28 + 22 + inner_h + 20  # top_pad + title_h + gap + content + bottom_pad

    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["border_cyan"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "AI 综合分析", "analysis", c["text_gold"], c["border_gold"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["border_cyan_dim"])
    draw.text((PAD + CARD_PAD, y + 14 + th + 22), wrapped,
              font=fonts.body, fill=c["text_bright"], spacing=7)
    return img, draw, card_h + 14


# ── 板块区块 ──────────────────────────────────────────────────────────────────

_SECTOR_PALETTE = [
    ("#FF1744", "#200009"),
    ("#FF6D00", "#1A0D00"),
    ("#FFD600", "#1A1400"),
    ("#00E5FF", "#00131A"),
    ("#00E676", "#00130A"),
    ("#D500F9", "#150022"),
    ("#FF4081", "#1A001B"),
    ("#40C4FF", "#001A22"),
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
                            "热门受益板块", "sectors", c["text_gold"], c["border_gold"], fonts)
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
                            "推荐关注标的", "stocks", c["text_orange"], c["border_orange"], fonts)
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

        _draw_neon_card(draw, sx, sy, col_w, sub_h,
                        border_color=c["border_orange"],
                        fill_color=c["surface2"], radius=6, border_width=1)

        draw.text((sx + 8, sy + 8), f"{i + 1:02d}", font=fonts.caption, fill=c["text_orange"])

        header = f"{code}  {name}" if code else name
        draw.text((sx + 36, sy + 6), header, font=fonts.h3, fill=c["text_white"])

        bar_w = col_w - 48
        _draw_neon_bar(draw, sx + 36, sy + 35, bar_w, 6, conf,
                       c1=c["bar_bull"], c2=c["bar_bull_end"])
        conf_text = f"{int(conf * 100)}%"
        ctw, _ = _text_wh(draw, conf_text, fonts.caption)
        draw.text((sx + col_w - ctw - 8, sy + 30), conf_text,
                  font=fonts.caption, fill=c["text_orange"])

        if logic:
            draw.text((sx + 8, sy + 52), _wrap(logic, chars=19),
                      font=fonts.caption, fill=c["text_cyan"])

    return img, draw, card_h + 14


# ── 风险提示区块（精确高度 + 修复双重绘制） ────────────────────────────────

def _calc_risks_h(draw, fonts, risks) -> int:
    """精确预计算风险区块内容高度"""
    _, title_th = _text_wh(draw, "关键风险提示", fonts.h2)
    th = title_th + 4
    total = 14 + th + 22

    for risk in risks[:4]:
        rw = _wrap(f"  >> {risk}", chars=30)
        total += _multiline_h(draw, rw, fonts.body, gap=6) + 10

    return total + 20


def _render_risks(img: Image.Image, draw: ImageDraw.Draw,
                   fonts: FontSet, y: int, risks: list) -> Tuple:
    c = THEME
    card_w = WIDTH - PAD * 2
    card_h = _calc_risks_h(draw, fonts, risks)

    # 使用 warning_bg 作为 fill_color，不再重复绘制矩形
    img = _draw_neon_card_with_shadow(img, PAD, y, card_w, card_h,
                                       border_color=c["warning_border"],
                                       fill_color=c["warning_bg"])
    draw = ImageDraw.Draw(img)

    th = _draw_block_title(draw, PAD + CARD_PAD, y + 14,
                            "关键风险提示", "risks", c["warning_text"], c["warning_border"], fonts)
    _draw_neon_divider(draw, PAD + 12, y + 14 + th + 8, card_w - 24, c["warning_border"])

    cy = y + 14 + th + 22
    for risk in risks[:4]:
        rw = _wrap(f"  >> {risk}", chars=30)
        draw.text((PAD + CARD_PAD, cy), rw, font=fonts.body,
                  fill=c["warning_text"], spacing=6)
        cy += _multiline_h(draw, rw, fonts.body, gap=6) + 10

    return img, draw, card_h + 14


# ── 页脚 ──────────────────────────────────────────────────────────────────────

def _render_footer(draw: ImageDraw.Draw, fonts: FontSet, y: int):
    c = THEME
    draw.line([(PAD, y + 4), (WIDTH - PAD, y + 4)], fill=c["border_cyan_dim"], width=1)
    draw.line([(PAD, y + 7), (WIDTH - PAD, y + 7)], fill=c["text_dim"], width=1)
    footer = "News-to-Stock AI Analyst  |  AI | 仅供参考，不构成投资建议"
    fw, _ = _text_wh(draw, footer, fonts.caption)
    draw.text(((WIDTH - fw) // 2, y + 16), footer, font=fonts.caption, fill=c["text_muted"])


# ── 主类 ──────────────────────────────────────────────────────────────────────

class MarketDailyVisualizer:
    """市场日报图生成器 v3.1 — 金融终端暗黑风格"""

    def __init__(self, theme: str = "dark"):
        self.theme = "dark"
        self.fonts = FontSet(str(DEFAULT_FONT), str(DEFAULT_FONT_BOLD))

    def generate(self, result, output_path: Optional[Path] = None) -> Path:
        fonts  = self.fonts
        rating = Rating.build(result.overall_rating)
        c      = THEME

        # ── 创建临时 draw 用于精确高度估算 ──
        tmp = Image.new("RGB", (1, 1))
        td = ImageDraw.Draw(tmp)

        # ── 精确估算各区块高度 ──
        header_h    = 190
        sentiment_h = _calc_sentiment_h(td, fonts, result, rating) + 14
        news_h      = _calc_news_h(td, fonts, result.top_news) + 14
        analysis_h  = _multiline_h(td, _wrap(result.market_summary, 32), fonts.body, 9) + 14 + 28 + 22 + 20 + 14
        sectors_h   = _est_sectors_h(result.hot_sectors) + 72 + 14
        stocks_h    = (math.ceil(min(8, len(result.hot_stocks)) / 2) * 96) + 94
        risks_h     = _calc_risks_h(td, fonts, result.key_risks) + 14
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
        logger.info(f"市场日报图已生成：{output_path}  ({WIDTH}x{actual_h})")
        return output_path

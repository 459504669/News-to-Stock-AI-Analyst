"""
可视化模块 v5.0 - 高清金融终端风格
解决：1) 布局现代化 2) 文字清晰度
策略：2x超采样渲染 + 现代网格布局 + 装饰性数据元素
"""
from pathlib import Path
from typing import Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import math
import random
from loguru import logger
from ai_analyst.rating_system import Rating

# ── 字体路径 ──────────────────────────────────────────────────────────────────
FONT_REG = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
FONT_BOLD = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-Bold.ttf"

# ── 超采样倍率（4x = 4倍分辨率渲染后缩放回原始尺寸，对应600DPI）──────────────────
SS = 4  # 超采样倍率（4x = 600DPI）
BASE_W = 1200  # 最终输出宽度
RENDER_W = BASE_W * SS  # 渲染画布宽度

# ── 配色方案：金融终端暗黑 Neon ───────────────────────────────────────────────
PALETTE = {
    "bg": "#050A14",
    "bg_grid": "#0A1525",
    "card": "#0D1B2A",
    "card_hover": "#111D2E",
    "border_cyan": "#00E5FF",
    "border_cyan_dim": "#004D5C",
    "border_gold": "#FFD600",
    "border_orange": "#FF6D00",
    "border_red": "#FF1744",
    "border_green": "#00E676",
    "border_purple": "#B388FF",
    "text_white": "#FFFFFF",
    "text_bright": "#E0F7FA",
    "text_cyan": "#4DD0E1",
    "text_gold": "#FFD600",
    "text_orange": "#FF9100",
    "text_red": "#FF5252",
    "text_green": "#69F0AE",
    "text_muted": "#4A6572",
    "text_dim": "#2A3F4D",
    "track": "#0D1E30",
    "bar_start": "#FF3D00",
    "bar_end": "#FF9100",
    "gauge_bg": "#0D1E30",
    "gauge_active": "#00E5FF",
    "sector_colors": [
        ("#FF1744", "#1A0008"), ("#FF6D00", "#1A0D00"),
        ("#FFD600", "#1A1400"), ("#00E5FF", "#00131A"),
        ("#00E676", "#00130A"), ("#B388FF", "#120022"),
        ("#FF4081", "#1A0010"), ("#40C4FF", "#001A22"),
    ],
}

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _hex(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(c1: str, c2: str, t: float) -> Tuple[int, int, int]:
    r1, g1, b1 = _hex(c1)
    r2, g2, b2 = _hex(c2)
    return int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t)


def _text_size(draw: ImageDraw.Draw, text: str, font) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _multiline_h(draw: ImageDraw.Draw, text: str, font, gap: int = 8) -> int:
    return sum(_text_size(draw, line, font)[1] + gap for line in text.split("\n"))


def _wrap_text(draw: ImageDraw.Draw, text: str, font, max_width: int) -> str:
    """基于像素宽度的智能文本换行（支持中文）"""
    if not text:
        return ""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        tw, _ = _text_size(draw, test_line, font)
        if tw > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return "\n".join(lines)


# ── 装饰性绘制函数 ────────────────────────────────────────────────────────────

def _draw_grid_bg(draw: ImageDraw.Draw, w: int, h: int, step: int = 80, color: str = "#0A1525"):
    """绘制背景网格线"""
    r, g, b = _hex(color)
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=(r, g, b, 30), width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(r, g, b, 30), width=1)


def _draw_card_neon(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                    border: str = "#00E5FF", fill: str = "#0D1B2A", r: int = 12, bw: int = 2):
    """霓虹卡片：双层边框 + 内阴影效果"""
    # 外层暗边框
    draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=r, fill=fill, outline="#0A1525", width=bw + 2)
    # 内层亮边框
    draw.rounded_rectangle([(x + 1, y + 1), (x + w - 1, y + h - 1)], radius=r - 1, outline=border, width=1)
    # 顶部高光条
    hr, hg, hb = _hex(border)
    draw.line([(x + r, y + 1), (x + w - r, y + 1)], fill=(min(hr + 60, 255), min(hg + 60, 255), min(hb + 60, 255)), width=2)


def _draw_gauge(draw: ImageDraw.Draw, cx: int, cy: int, radius: int, value: float,
                color: str = "#00E5FF", bg: str = "#0D1E30"):
    """绘制半圆仪表盘（value: 0-1）"""
    # 背景弧
    for angle in range(180, 360, 2):
        rad = math.radians(angle)
        x1 = cx + int((radius - 8) * math.cos(rad))
        y1 = cy + int((radius - 8) * math.sin(rad))
        x2 = cx + int(radius * math.cos(rad))
        y2 = cy + int(radius * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=bg, width=3)

    # 活动弧
    arc_len = int(180 * value)
    for angle in range(180, 180 + arc_len, 2):
        rad = math.radians(angle)
        t = (angle - 180) / 180
        r, g, b = _lerp(color, "#FF1744", t * 0.5)
        x1 = cx + int((radius - 8) * math.cos(rad))
        y1 = cy + int((radius - 8) * math.sin(rad))
        x2 = cx + int(radius * math.cos(rad))
        y2 = cy + int(radius * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=4)

    # 指针
    ptr_angle = math.radians(180 + arc_len)
    px = cx + int((radius - 4) * math.cos(ptr_angle))
    py = cy + int((radius - 4) * math.sin(ptr_angle))
    draw.ellipse([(px - 6, py - 6), (px + 6, py + 6)], fill=color)
    draw.ellipse([(px - 3, py - 3), (px + 3, py + 3)], fill="#FFFFFF")


def _draw_bar_chart(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                    values: List[float], colors: List[str]):
    """绘制横向条形图"""
    if not values:
        return
    bar_h = h // len(values)
    max_v = max(values) if max(values) > 0 else 1
    for i, (v, c) in enumerate(zip(values, colors)):
        by = y + i * bar_h + 4
        bw = int((w - 60) * v / max_v)
        # 轨道
        draw.rounded_rectangle([(x + 50, by + 6), (x + w - 10, by + bar_h - 6)],
                               radius=(bar_h - 12) // 2, fill=PALETTE["track"])
        # 填充
        if bw > 4:
            draw.rounded_rectangle([(x + 50, by + 6), (x + 50 + bw, by + bar_h - 6)],
                                   radius=(bar_h - 12) // 2, fill=c)
        # 数值标签
        draw.text((x + 10, by + 4), f"{int(v * 100)}%", font=None, fill=c)


def _draw_sparkline(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                    color: str = "#00E5FF", points: int = 20):
    """绘制装饰性迷你折线图"""
    random.seed(42)
    pts = []
    for i in range(points):
        px = x + int(w * i / (points - 1))
        py = y + h // 2 + random.randint(-h // 3, h // 3)
        pts.append((px, py))
    # 绘制线
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=2)
    # 绘制点
    for px, py in pts[::4]:
        draw.ellipse([(px - 3, py - 3), (px + 3, py + 3)], fill=color)


def _draw_dashed_line(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int,
                      color: str = "#4A6572", dash: int = 8):
    """绘制虚线"""
    length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    steps = int(length / dash)
    for i in range(0, steps, 2):
        sx = int(x1 + dx * i * dash)
        sy = int(y1 + dy * i * dash)
        ex = int(x1 + dx * min((i + 1) * dash, length))
        ey = int(y1 + dy * min((i + 1) * dash, length))
        draw.line([(sx, sy), (ex, ey)], fill=color, width=1)


def _draw_hex_badge(draw: ImageDraw.Draw, cx: int, cy: int, text: str, text_color: str,
                    bg_color: str, font, radius: int = 36):
    """绘制六边形徽章"""
    pts = []
    for i in range(6):
        angle = math.radians(30 + i * 60)
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        pts.append((px, py))
    draw.polygon(pts, fill=bg_color, outline=text_color, width=2)
    tw, th = _text_size(draw, text, font)
    draw.text((cx - tw // 2, cy - th // 2), text, font=font, fill=text_color)


# ── 字体管理 ──────────────────────────────────────────────────────────────────

class Fonts:
    def __init__(self, reg: str, bold: str):
        try:
            self.tiny = ImageFont.truetype(reg, 18 * SS)
            self.small = ImageFont.truetype(reg, 22 * SS)
            self.body = ImageFont.truetype(reg, 28 * SS)
            self.body_b = ImageFont.truetype(bold, 28 * SS)
            self.h3 = ImageFont.truetype(bold, 32 * SS)
            self.h2 = ImageFont.truetype(bold, 40 * SS)
            self.h1 = ImageFont.truetype(bold, 52 * SS)
            self.hero = ImageFont.truetype(bold, 72 * SS)
            self.score = ImageFont.truetype(bold, 96 * SS)
            self.micro = ImageFont.truetype(reg, 14 * SS)
        except IOError:
            d = ImageFont.load_default()
            for a in ["tiny", "small", "body", "body_b", "h3", "h2", "h1", "hero", "score", "micro"]:
                setattr(self, a, d)


# ── 主生成器 ──────────────────────────────────────────────────────────────────

class Visualizer:
    """高清金融终端风格分析图生成器"""

    def __init__(self, theme: str = "dark", width: int = BASE_W):
        self.theme = theme
        self.width = width
        self.fonts = Fonts(str(FONT_REG), str(FONT_BOLD))

    def generate(self, news_title: str, news_source: str, news_time: str,
                 rating_score: int, analysis_summary: str,
                 beneficiary_sectors: List[str], recommended_stocks: List[dict],
                 risks: List[str], output_path: Optional[Path] = None) -> Path:

        f = self.fonts
        c = PALETTE
        rating = Rating.build(rating_score)
        rating_color = c["border_red"] if rating_score >= 4 else c["border_green"] if rating_score <= 2 else c["text_muted"]

        # ── 预计算尺寸 ────────────────────────────────────────────────────────
        tmp = Image.new("RGB", (1, 1))
        td = ImageDraw.Draw(tmp)

        # 标题区域可用宽度（左侧卡片宽度 - 左右padding）
        title_max_w = int(RENDER_W * 0.52) - 128 * SS
        title_wrapped = _wrap_text(td, news_title, f.h2, title_max_w)
        title_h = _multiline_h(td, title_wrapped, f.h2, gap=12)

        # 分析文本可用宽度（全宽卡片 - 左右padding）
        summary_max_w = RENDER_W - 80 * SS - 104 * SS
        summary_wrapped = _wrap_text(td, analysis_summary, f.body, summary_max_w)
        summary_h = _multiline_h(td, summary_wrapped, f.body, gap=12)

        # ── 计算总高度 ────────────────────────────────────────────────────────
        header_h = 220 * SS
        title_card_h = title_h + 160 * SS
        gauge_h = 280 * SS
        summary_card_h = summary_h + 100 * SS
        sectors_card_h = max(math.ceil(len(beneficiary_sectors) / 3) * 60 * SS + 80 * SS, 200 * SS)
        stocks_card_h = len(recommended_stocks[:4]) * 90 * SS + 80 * SS
        risks_card_h = len(risks[:3]) * 60 * SS + 80 * SS
        footer_h = 60 * SS

        # 双栏区域高度
        dual_h = max(sectors_card_h, stocks_card_h)

        total_h = (header_h + title_card_h + gauge_h + summary_card_h +
                   dual_h + risks_card_h + footer_h + 140 * SS)

        # ── 创建画布 ──────────────────────────────────────────────────────────
        img = Image.new("RGB", (RENDER_W, total_h), color=c["bg"])
        draw = ImageDraw.Draw(img)

        # 背景网格
        _draw_grid_bg(draw, RENDER_W, total_h, step=100 * SS)

        y = 20 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 1. HEADER 区域（带迷你折线装饰）
        # ═══════════════════════════════════════════════════════════════════════
        for py in range(y, y + header_h):
            t = (py - y) / header_h
            color = _lerp("#030810", "#0A1525", t)
            draw.line([(0, py), (RENDER_W, py)], fill=color)

        # 顶部装饰线
        draw.line([(0, y), (RENDER_W, y)], fill=c["border_cyan_dim"], width=2 * SS)
        draw.line([(0, y + header_h - 2), (RENDER_W, y + header_h - 2)], fill=c["border_cyan"], width=3 * SS)

        # 标题
        draw.text((40 * SS, y + 30 * SS), "AI MARKET TERMINAL", font=f.h3, fill=c["text_cyan"])
        draw.text((40 * SS, y + 80 * SS), "新闻分析报告", font=f.hero, fill=c["text_white"])

        # 右侧迷你折线装饰
        _draw_sparkline(draw, RENDER_W - 320 * SS, y + 50 * SS, 280 * SS, 100 * SS, color=c["border_cyan_dim"])

        # 右上角评级胶囊
        score_text = rating.label
        tw, th = _text_size(draw, score_text, f.h2)
        badge_w, badge_h = tw + 48 * SS, th + 28 * SS
        bx = RENDER_W - badge_w - 40 * SS
        by = y + 40 * SS
        draw.rounded_rectangle([(bx, by), (bx + badge_w, by + badge_h)],
                               radius=12 * SS, fill=c["card"], outline=rating_color, width=2 * SS)
        draw.text((bx + 24 * SS, by + 14 * SS), score_text, font=f.h2, fill=rating_color)

        # 星级
        stars = rating.stars
        stw, _ = _text_size(draw, stars, f.h1)
        draw.text((RENDER_W - stw - 40 * SS, by + badge_h + 12 * SS), stars, font=f.h1, fill=rating_color)

        # 底部信息
        info_y = y + header_h - 50 * SS
        draw.text((40 * SS, info_y), f"{news_time}  |  来源：{news_source}", font=f.small, fill=c["text_cyan"])

        y += header_h + 16 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 2. 顶部双栏：标题卡片 + 评级仪表盘
        # ═══════════════════════════════════════════════════════════════════════
        col_gap = 20 * SS
        left_w = int(RENDER_W * 0.52) - col_gap // 2
        right_w = RENDER_W - left_w - col_gap - 80 * SS

        # 左栏：标题卡片
        card_h = max(title_card_h, gauge_h)
        _draw_card_neon(draw, 40 * SS, y, left_w, card_h, border=c["border_cyan"])

        # 标题区块图标
        draw.rounded_rectangle([(64 * SS, y + 24 * SS), (68 * SS, y + 56 * SS)],
                               radius=2 * SS, fill=c["border_gold"])
        draw.text((84 * SS, y + 24 * SS), "新闻标题", font=f.h2, fill=c["text_gold"])

        # 标题文字
        ty = y + 70 * SS
        for line in title_wrapped.split("\n"):
            draw.text((64 * SS, ty), line, font=f.h2, fill=c["text_white"])
            _, lh = _text_size(draw, line, f.h2)
            ty += lh + 12

        # 右栏：评级仪表盘卡片
        rx = 40 * SS + left_w + col_gap
        _draw_card_neon(draw, rx, y, right_w, card_h, border=rating_color)

        # 仪表盘标题
        draw.text((rx + 24 * SS, y + 20 * SS), "市场影响评级", font=f.h3, fill=rating_color)

        # 圆形仪表盘
        gauge_cx = rx + right_w // 2
        gauge_cy = y + card_h // 2 + 20 * SS
        gauge_r = min(right_w, card_h) // 2 - 40 * SS

        # 外圆环
        draw.ellipse([(gauge_cx - gauge_r, gauge_cy - gauge_r),
                      (gauge_cx + gauge_r, gauge_cy + gauge_r)],
                     outline=c["track"], width=8 * SS)
        # 活动弧
        _draw_gauge(draw, gauge_cx, gauge_cy, gauge_r, rating_score / 5, color=rating_color)

        # 中心分数
        score_str = str(rating_score)
        s_tw, s_th = _text_size(draw, score_str, f.score)
        draw.text((gauge_cx - s_tw // 2, gauge_cy - s_th // 2 - 10 * SS),
                  score_str, font=f.score, fill=c["text_white"])

        # 评级标签
        lbl = rating.label
        l_tw, l_th = _text_size(draw, lbl, f.h3)
        draw.text((gauge_cx - l_tw // 2, gauge_cy + gauge_r // 2 + 10 * SS),
                  lbl, font=f.h3, fill=rating_color)

        y += card_h + 16 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 3. AI 详细解读（全宽卡片）
        # ═══════════════════════════════════════════════════════════════════════
        card_w = RENDER_W - 80 * SS
        card_h = summary_card_h
        _draw_card_neon(draw, 40 * SS, y, card_w, card_h, border=c["border_cyan"])

        # 标题行
        draw.rounded_rectangle([(64 * SS, y + 24 * SS), (68 * SS, y + 56 * SS)],
                               radius=2 * SS, fill=c["border_gold"])
        draw.text((84 * SS, y + 24 * SS), "AI 详细解读", font=f.h2, fill=c["text_gold"])

        # 分析文字
        draw.text((64 * SS, y + 72 * SS), summary_wrapped,
                  font=f.body, fill=c["text_bright"], spacing=12)

        y += card_h + 16 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 4. 双栏：受益板块 + 推荐标的
        # ═══════════════════════════════════════════════════════════════════════
        dual_h = max(sectors_card_h, stocks_card_h)

        # 左栏：受益板块
        _draw_card_neon(draw, 40 * SS, y, left_w, dual_h, border=c["border_orange"])
        draw.rounded_rectangle([(64 * SS, y + 24 * SS), (68 * SS, y + 56 * SS)],
                               radius=2 * SS, fill=c["border_orange"])
        draw.text((84 * SS, y + 24 * SS), "受益板块", font=f.h2, fill=c["text_orange"])

        # 板块标签（3列网格）
        tag_start_y = y + 76 * SS
        tag_col_w = (left_w - 48 * SS) // 3
        for i, sector in enumerate(beneficiary_sectors[:9]):
            row = i // 3
            col = i % 3
            tx = 64 * SS + col * (tag_col_w + 8 * SS)
            ty = tag_start_y + row * 56 * SS
            fg, bg = c["sector_colors"][i % len(c["sector_colors"])]
            tw, th = _text_size(draw, sector, f.small)
            tw = max(tw + 24 * SS, tag_col_w - 8 * SS)
            draw.rounded_rectangle([(tx, ty), (tx + tw, ty + 40 * SS)],
                                   radius=6 * SS, fill=bg, outline=fg, width=2 * SS)
            draw.text((tx + 12 * SS, ty + 8 * SS), sector, font=f.small, fill=fg)

        # 右栏：推荐标的
        rx = 40 * SS + left_w + col_gap
        _draw_card_neon(draw, rx, y, right_w, dual_h, border=c["border_red"])
        draw.rounded_rectangle([(rx + 24 * SS, y + 24 * SS), (rx + 28 * SS, y + 56 * SS)],
                               radius=2 * SS, fill=c["border_red"])
        draw.text((rx + 44 * SS, y + 24 * SS), "推荐关注标的", font=f.h2, fill=c["text_orange"])

        # 标的列表
        sy = y + 76 * SS
        for i, stock in enumerate(recommended_stocks[:4]):
            code = stock.get("code", "")
            name = stock.get("name", "")
            logic = stock.get("logic", "")[:40]
            conf = stock.get("confidence", 0.7)

            if conf >= 0.85:
                conf_color, level = c["border_red"], "强烈推荐"
            elif conf >= 0.70:
                conf_color, level = c["border_orange"], "比较推荐"
            else:
                conf_color, level = c["border_gold"], "一般推荐"

            # 代码名称
            header = f"{code}  {name}" if code else name
            draw.text((rx + 24 * SS, sy), header, font=f.body_b, fill=c["text_white"])

            # 进度条
            bar_w = right_w - 56 * SS
            bar_y = sy + 36 * SS
            draw.rounded_rectangle([(rx + 24 * SS, bar_y), (rx + 24 * SS + bar_w, bar_y + 10 * SS)],
                                   radius=5 * SS, fill=c["track"])
            fill_w = int(bar_w * conf)
            if fill_w > 4:
                for j in range(fill_w):
                    t = j / max(fill_w - 1, 1)
                    col = _lerp(c["bar_start"], c["bar_end"], t)
                    draw.line([(rx + 24 * SS + j, bar_y + 2), (rx + 24 * SS + j, bar_y + 8 * SS)], fill=col)

            # 百分比 + 等级
            pct = f"{int(conf * 100)}%"
            draw.text((rx + 24 * SS, bar_y + 14 * SS), pct, font=f.micro, fill=conf_color)
            draw.text((rx + 80 * SS, bar_y + 14 * SS), level, font=f.micro, fill=conf_color)

            # 逻辑简述
            if logic:
                draw.text((rx + 24 * SS, bar_y + 32 * SS), logic, font=f.tiny, fill=c["text_cyan"])

            sy += 90 * SS

        y += dual_h + 16 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 5. 风险提示（全宽，橙色警告风格）
        # ═══════════════════════════════════════════════════════════════════════
        if risks:
            card_w = RENDER_W - 80 * SS
            card_h = risks_card_h
            _draw_card_neon(draw, 40 * SS, y, card_w, card_h,
                            border=c["border_orange"], fill="#100A00")

            draw.rounded_rectangle([(64 * SS, y + 24 * SS), (68 * SS, y + 56 * SS)],
                                   radius=2 * SS, fill=c["border_orange"])
            draw.text((84 * SS, y + 24 * SS), "关键风险提示", font=f.h2, fill=c["text_orange"])

            ry = y + 76 * SS
            for risk in risks[:3]:
                # 警告三角
                tri_cx = 72 * SS
                tri_cy = ry + 12 * SS
                draw.polygon([(tri_cx, tri_cy - 8 * SS), (tri_cx - 8 * SS, tri_cy + 6 * SS),
                              (tri_cx + 8 * SS, tri_cy + 6 * SS)],
                             outline=c["border_orange"], width=2 * SS)
                draw.line([(tri_cx, tri_cy - 2 * SS), (tri_cx, tri_cy + 2 * SS)],
                          fill=c["border_orange"], width=2 * SS)

                rw = textwrap.fill(risk, width=36)
                draw.text((92 * SS, ry), rw, font=f.body, fill=c["text_orange"], spacing=10)
                ry += _multiline_h(draw, rw, f.body, gap=10) + 16 * SS

            y += card_h + 16 * SS

        # ═══════════════════════════════════════════════════════════════════════
        # 6. 页脚
        # ═══════════════════════════════════════════════════════════════════════
        draw.line([(40 * SS, y + 8 * SS), (RENDER_W - 40 * SS, y + 8 * SS)],
                  fill=c["border_cyan_dim"], width=2 * SS)
        footer = "News-to-Stock AI Analyst  |  AI生成，仅供参考，不构成投资建议"
        fw, _ = _text_size(draw, footer, f.small)
        draw.text(((RENDER_W - fw) // 2, y + 20 * SS), footer, font=f.small, fill=c["text_muted"])

        # ═══════════════════════════════════════════════════════════════════════
        # 7. 后处理：缩放回目标尺寸
        # ═══════════════════════════════════════════════════════════════════════
        actual_h = y + 60 * SS
        img = img.crop((0, 0, RENDER_W, actual_h))

        # 使用 LANCZOS 高质量缩放
        out_w = BASE_W
        out_h = int(actual_h / SS)
        img = img.resize((out_w, out_h), Image.LANCZOS)

        # 轻微锐化增强文字边缘
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3)

        # 保存（高DPI + 高质量）
        if output_path is None:
            output_path = Path("output") / "images" / "analysis_latest.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG", optimize=True, dpi=(600, 600))
        logger.info(f"高清分析图已生成：{output_path}  ({out_w}x{out_h} @ 600dpi)")
        return output_path

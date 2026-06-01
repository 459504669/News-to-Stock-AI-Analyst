"""
评级系统 - 将数字评分映射为文字标签与视觉样式
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class RatingLevel(IntEnum):
    """5档评分枚举"""
    STRONG_BEARISH = 1   # 强烈利空
    BEARISH = 2            # 利空
    NEUTRAL = 3            # 中性
    BULLISH = 4            # 利好
    STRONG_BULLISH = 5     # 强烈利好

    @property
    def label(self) -> str:
        labels = {
            1: "强烈利空",
            2: "利空",
            3: "中性",
            4: "利好",
            5: "强烈利好",
        }
        return labels[self.value]

    @property
    def stars(self) -> str:
        """星级表示（★ 为实心，☆ 为空心）"""
        return "★" * self.value + "☆" * (5 - self.value)

    @property
    def color(self) -> str:
        """对应颜色（中国股市惯例：红=涨/利好，绿=跌/利空）"""
        colors = {
            1: "#008000",   # 绿色 - 强烈利空
            2: "#32CD32",   # 浅绿 - 利空
            3: "#808080",   # 灰色 - 中性
            4: "#FF4500",   # 橙红 - 利好
            5: "#FF0000",   # 红色 - 强烈利好
        }
        return colors[self.value]

    @property
    def emoji(self) -> str:
        emojis = {
            1: "🔴",
            2: "🟢",
            3: "⚪",
            4: "🔶",
            5: "🔥",
        }
        return emojis[self.value]

    @classmethod
    def from_score(cls, score: int) -> "RatingLevel":
        score = max(1, min(5, score))
        return cls(score)


@dataclass
class Rating:
    """完整评级对象"""
    score: int
    label: str
    stars: str
    color: str
    emoji: str

    @classmethod
    def build(cls, score: int) -> "Rating":
        level = RatingLevel.from_score(score)
        return cls(
            score=level.value,
            label=level.label,
            stars=level.stars,
            color=level.color,
            emoji=level.emoji,
        )

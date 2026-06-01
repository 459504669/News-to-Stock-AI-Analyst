"""
分析功能测试脚本
用法：python scripts/test_analysis.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger
from ai_analyst.analyzer import Analyzer
from visualizer.generator import Visualizer


SAMPLE_NEWS = {
    "title": "央行宣布降准0.5个百分点 释放长期资金约1万亿元",
    "content": (
        "中国人民银行决定于2026年6月15日下调金融机构存款准备金率0.5个百分点，"
        "此次降准预计释放长期资金约1万亿元，旨在进一步支持实体经济发展，"
        "促进综合融资成本稳中有降。此次降准为全面降准，除已执行5%存款准备金率的部分"
        "县域法人金融机构外，对其他金融机构普遍下调存款准备金率0.5个百分点。"
        "本次下调后，金融机构加权平均存款准备金率约为7.0%。"
    ),
    "source": "新华社财经",
    "published_at": "2026-06-01 10:00:00",
}


def main():
    logger.info("🚀 开始测试 AI 分析流程...")

    # 1. AI 分析
    analyzer = Analyzer(llm_provider="openai", llm_model="gpt-4o")
    logger.info(f"分析新闻：{SAMPLE_NEWS['title']}")
    result = analyzer.analyze(
        title=SAMPLE_NEWS["title"],
        content=SAMPLE_NEWS["content"],
        source=SAMPLE_NEWS["source"],
        published_at=SAMPLE_NEWS["published_at"],
    )

    if not result:
        logger.error("❌ AI 分析失败，请检查 API Key 和网络连接")
        return

    logger.success(f"✅ 分析完成！评分：{result.rating_label} {result.rating}")

    # 2. 打印分析结果
    print("\n" + "=" * 60)
    print(f"📰 标题：{SAMPLE_NEWS['title']}")
    print(f"⚡ 评级：{result.rating_label}（{result.rating}/5）")
    print(f"📊 置信度：{result.confidence:.0%}")
    print(f"\n📝 分析摘要：\n{result.summary}")
    print(f"\n🎯 受益板块：{', '.join(result.beneficiary_sectors)}")
    print(f"\n📈 推荐标的：")
    for stock in result.recommended_stocks[:5]:
        print(f"  • {stock.get('code', '')} {stock.get('name', '')}：{stock.get('logic', '')}")
    print(f"\n⚠️ 风险提示：")
    for risk in result.risks:
        print(f"  • {risk}")
    print("=" * 60 + "\n")

    # 3. 生成图片
    logger.info("🖼️  开始生成分析图片...")
    viz = Visualizer()
    output_path = viz.generate(
        news_title=SAMPLE_NEWS["title"],
        news_source=SAMPLE_NEWS["source"],
        news_time=SAMPLE_NEWS["published_at"],
        rating_score=result.rating,
        analysis_summary=result.summary,
        beneficiary_sectors=result.beneficiary_sectors,
        recommended_stocks=result.recommended_stocks,
        risks=result.risks,
    )
    logger.success(f"🎉 分析图已生成：{output_path}")


if __name__ == "__main__":
    main()

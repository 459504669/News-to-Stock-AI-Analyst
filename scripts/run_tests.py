"""
综合测试脚本 - 验证所有核心模块功能
"""
import sys
from pathlib import Path
from datetime import datetime

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """测试 1：所有模块能否正常导入"""
    print("=" * 60)
    print("测试 1：模块导入")
    print("=" * 60)

    try:
        from news_collector.base import BaseCollector, NewsItem
        print("  ✅ news_collector.base")
    except Exception as e:
        print(f"  ❌ news_collector.base: {e}")

    try:
        from news_collector.deduplicator import deduplicate, similarity
        print("  ✅ news_collector.deduplicator")
    except Exception as e:
        print(f"  ❌ news_collector.deduplicator: {e}")

    try:
        from news_collector.scheduler import NewsScheduler
        print("  ✅ news_collector.scheduler")
    except Exception as e:
        print(f"  ❌ news_collector.scheduler: {e}")

    try:
        from ai_analyst.rating_system import RatingLevel, Rating
        print("  ✅ ai_analyst.rating_system")
    except Exception as e:
        print(f"  ❌ ai_analyst.rating_system: {e}")

    try:
        from ai_analyst.analyzer import Analyzer, NewsAnalysisResult
        print("  ✅ ai_analyst.analyzer")
    except Exception as e:
        print(f"  ❌ ai_analyst.analyzer: {e}")

    try:
        from ai_analyst.llm_client import LLMClient
        print("  ✅ ai_analyst.llm_client")
    except Exception as e:
        print(f"  ❌ ai_analyst.llm_client: {e}")

    try:
        from visualizer.generator import Visualizer
        print("  ✅ visualizer.generator")
    except Exception as e:
        print(f"  ❌ visualizer.generator: {e}")

    try:
        from database.models import Database, News, AnalysisResult
        print("  ✅ database.models")
    except Exception as e:
        print(f"  ❌ database.models: {e}")

    try:
        from database.crud import create_news, create_analysis, list_recent_news
        print("  ✅ database.crud")
    except Exception as e:
        print(f"  ❌ database.crud: {e}")

    try:
        from api.schemas import AnalyzeRequest, NewsItemOut, AnalysisOut
        print("  ✅ api.schemas")
    except Exception as e:
        print(f"  ❌ api.schemas: {e}")

    print()


def test_rating_system():
    """测试 2：评级系统"""
    print("=" * 60)
    print("测试 2：评级系统")
    print("=" * 60)

    from ai_analyst.rating_system import RatingLevel, Rating

    for score in range(1, 6):
        level = RatingLevel.from_score(score)
        rating = Rating.build(score)
        print(f"  评分 {score}: {rating.label} {rating.stars} {rating.color}")

    # 边界测试
    assert RatingLevel.from_score(0).value == 1, "评分 0 应该映射到 1"
    assert RatingLevel.from_score(10).value == 5, "评分 10 应该映射到 5"
    print("  ✅ 边界值测试通过")

    # 数据类测试
    r = Rating.build(4)
    assert r.score == 4
    assert r.label == "利好"
    print("  ✅ 数据类构建正确")
    print()


def test_deduplicator():
    """测试 3：新闻去重"""
    print("=" * 60)
    print("测试 3：新闻去重器")
    print("=" * 60)

    from news_collector.base import NewsItem
    from news_collector.deduplicator import deduplicate, similarity

    now = datetime.now()

    items = [
        NewsItem(
            title="央行降准50个基点释放流动性",
            summary="test", content="test",
            source="财联社", url="http://a.com/1",
            published_at=now,
        ),
        NewsItem(
            title="央行宣布降准50BP释放万亿流动性",
            summary="test2", content="test2",
            source="新浪财经", url="http://b.com/2",
            published_at=now.replace(minute=now.minute + 1),
        ),
        NewsItem(
            title="美联储维持利率不变",
            summary="test3", content="test3",
            source="路透社", url="http://c.com/3",
            published_at=now,
        ),
    ]

    result = deduplicate(items, threshold=0.7)
    assert len(result) == 2, f"去重后应为 2 条，实际 {len(result)} 条"
    print(f"  ✅ 去重：3 条 → {len(result)} 条（相似标题已合并）")

    sim = similarity("央行降准", "央行宣布降准")
    assert sim > 0.5, "相似文本相似度应大于 0.5"
    print(f"  ✅ 相似度计算正常：'央行降准' vs '央行宣布降准' = {sim:.2f}")
    print()


def test_database():
    """测试 4：数据库模块"""
    print("=" * 60)
    print("测试 4：数据库模块")
    print("=" * 60)

    import os
    import tempfile

    from database.models import Database, News, AnalysisResult
    from database.crud import (
        create_news, create_analysis,
        list_recent_news, list_recent_analyses,
        get_news_by_url, get_analysis_by_news_id,
    )

    # 使用临时数据库
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    db = Database(url=f"sqlite:///{db_path}")
    db.create_tables()

    # 创建新闻
    session = db.get_session()
    news = create_news(
        db=session,
        title="测试新闻标题",
        summary="测试摘要",
        content="测试内容",
        source="测试来源",
        url="http://test.com/1",
        published_at=datetime.now(),
    )
    assert news.id is not None, "新闻 ID 不应为空"
    print(f"  ✅ 创建新闻：id={news.id}, title={news.title}")

    # 查询新闻
    found = get_news_by_url(session, "http://test.com/1")
    assert found is not None, "应能按 URL 查到新闻"
    assert found.title == "测试新闻标题"
    print("  ✅ URL 查询正常")

    # 创建分析结果
    analysis = create_analysis(
        db=session,
        news_id=news.id,
        rating=4,
        rating_label="利好",
        summary="测试分析文本",
        beneficiary_sectors=["金融", "地产"],
        recommended_stocks=[{"code": "601398", "name": "工商银行", "logic": "降准利好银行"}],
        risks=["政策落地不及预期"],
        time_horizon="short",
        confidence=0.8,
        image_path="/tmp/test.png",
    )
    assert analysis.id is not None
    print(f"  ✅ 创建分析：id={analysis.id}, rating={analysis.rating}")

    # 查询分析
    found_a = get_analysis_by_news_id(session, news.id)
    assert found_a is not None
    assert found_a.rating_label == "利好"
    print("  ✅ 分析查询正常")

    # 列表查询
    news_list = list_recent_news(session, limit=10)
    assert len(news_list) == 1
    analysis_list = list_recent_analyses(session, limit=10)
    assert len(analysis_list) == 1
    print("  ✅ 列表查询正常")

    session.close()

    db.close()
    os.unlink(db_path)
    print("  ✅ 数据库测试通过")
    print()


def test_visualizer():
    """测试 5：可视化模块（生成示例图片）"""
    print("=" * 60)
    print("测试 5：可视化图片生成")
    print("=" * 60)

    from visualizer.generator import Visualizer

    output_dir = PROJECT_ROOT / "output" / "images"
    output_path = output_dir / "test_sample.png"

    viz = Visualizer(theme="light")
    result = viz.generate(
        news_title="美联储宣布维持利率不变，暗示年内可能降息",
        news_source="路透社",
        news_time="2026-06-01 08:30",
        rating_score=4,
        analysis_summary=(
            "美联储在6月FOMC会议上宣布维持联邦基金利率在5.25%-5.50%区间不变，"
            "符合市场预期。声明中删除了'通胀偏高'的表述，改为'通胀已取得进一步进展'，"
            "被市场解读为鸽派信号。点阵图显示多数委员预计年内将降息2次。"
            "声明发布后，美股三大指数快速拉升，10年期美债收益率下行5个基点，"
            "黄金价格突破新高。市场对降息预期明显升温。"
        ),
        beneficiary_sectors=["科技成长", "黄金", "房地产", "债券"],
        recommended_stocks=[
            {"code": "518880", "name": "黄金ETF", "logic": "降息预期推动金价上行"},
            {"code": "NVDA", "name": "英伟达", "logic": "降息利好科技股估值"},
            {"code": "603019", "name": "中科新材", "logic": "受益于全球降息周期"},
        ],
        risks=[
            "通胀反弹风险：若后续CPI数据超预期，降息计划可能推迟",
            "就业市场过热：强劲就业数据可能制约降息空间",
            "地缘政治风险：中东局势紧张可能推升油价和通胀",
        ],
        output_path=output_path,
    )

    assert output_path.exists(), f"图片应存在：{output_path}"
    assert output_path.stat().st_size > 10000, "图片大小应大于 10KB"
    print(f"  ✅ 亮色主题图片生成：{output_path} ({output_path.stat().st_size // 1024}KB)")

    # 暗色主题
    dark_path = output_dir / "test_sample_dark.png"
    viz_dark = Visualizer(theme="dark")
    viz_dark.generate(
        news_title="欧佩克+宣布大幅减产，国际油价飙升",
        news_source="彭博社",
        news_time="2026-06-01 06:00",
        rating_score=5,
        analysis_summary="欧佩克+在紧急会议上决定将日产量削减200万桶，远超市场预期的100万桶。国际原油价格应声大涨。",
        beneficiary_sectors=["石油开采", "新能源", "煤炭"],
        recommended_stocks=[
            {"code": "600938", "name": "中国海油", "logic": "直接受益于油价上涨"},
        ],
        risks=["全球经济衰退可能压制需求"],
        output_path=dark_path,
    )
    assert dark_path.exists()
    print(f"  ✅ 暗色主题图片生成：{dark_path} ({dark_path.stat().st_size // 1024}KB)")
    print()


def test_api_schemas():
    """测试 6：API Schema 模型"""
    print("=" * 60)
    print("测试 6：API Schema")
    print("=" * 60)

    from api.schemas import AnalyzeRequest, AnalysisOut
    from datetime import datetime

    # 验证请求模型
    req = AnalyzeRequest(
        title="测试标题",
        content="测试内容",
        source="测试来源",
    )
    assert req.title == "测试标题"
    print("  ✅ AnalyzeRequest 构建正确")

    # 验证响应模型
    resp = AnalysisOut(
        id=1,
        news_id=1,
        title="测试",
        rating=4,
        rating_label="利好",
        summary="测试分析",
        beneficiary_sectors=["科技"],
        recommended_stocks=[{"code": "000001", "name": "测试", "logic": "测试逻辑"}],
        risks=["测试风险"],
        image_path="/tmp/test.png",
    )
    assert resp.rating == 4
    assert resp.beneficiary_sectors == ["科技"]
    print("  ✅ AnalysisOut 构建正确")
    print()


def test_fastapi_app():
    """测试 7：FastAPI 应用（仅验证路由注册，不实际调用 LLM）"""
    print("=" * 60)
    print("测试 7：FastAPI 路由")
    print("=" * 60)

    from api.main import app

    routes = [r.path for r in app.routes]
    print(f"  注册路由数：{len(routes)}")
    for r in routes:
        print(f"    {r}")

    assert "/" in routes
    assert "/api/news/latest" in routes
    assert "/api/analyze" in routes
    assert "/api/analysis/latest" in routes
    assert "/api/image/{analysis_id}" in routes
    print("  ✅ 所有预期路由已注册")
    print()


if __name__ == "__main__":
    print("\n" + "🚀 新闻抓取AI分析 综合测试".center(60, "="))
    print()

    try:
        test_imports()
        test_rating_system()
        test_deduplicator()
        test_database()
        test_visualizer()
        test_api_schemas()
        test_fastapi_app()

        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

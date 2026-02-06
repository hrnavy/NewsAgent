"""
入口脚本：发现新闻 + 逐篇事实核查（Serper）→ 汇总报告。
逻辑位于 news_verify 包，此处仅作命令行入口与兼容导入。
"""
from news_verify import run_news_fact_check

__all__ = ["run_news_fact_check"]

if __name__ == "__main__":
    portal = input("请输入新闻门户首页 URL: ").strip()
    if not portal:
        portal = "https://news.yahoo.com/"

    interests = input("请输入你的兴趣点描述（中文或英文）: ").strip()
    if not interests:
        interests = "我对人工智能、科技公司、宏观经济比较感兴趣"

    out_articles = input("文章保存目录 (默认: data/articles): ").strip() or "data/articles"
    out_reports = input("报告保存目录 (默认: reports): ").strip() or "reports"

    report = run_news_fact_check(
        portal,
        interests,
        articles_dir=out_articles,
        reports_dir=out_reports,
    )
    print("\n================= 事实核查报告 =================\n")
    print(report)

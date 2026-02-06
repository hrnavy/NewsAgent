"""
入口脚本：发现新闻 + 逐篇验证（计划 + Serper）→ 汇总报告。
逻辑位于 news_verify 包，此处仅作命令行入口与兼容导入。
"""
from news_verify import run_discover_and_verify

__all__ = ["run_discover_and_verify"]

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        portal = sys.argv[1]
        interests = sys.argv[2]
        max_articles = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    else:
        portal = input("请输入新闻门户首页 URL（默认 https://news.yahoo.com/）: ").strip() or "https://news.yahoo.com/"
        interests = input("请输入兴趣描述（默认：人工智能、科技）: ").strip() or "我对人工智能、科技公司、宏观经济比较感兴趣"
        max_articles = input("最多验证几篇新闻（默认 3）: ").strip() or "3"
        try:
            max_articles = int(max_articles)
        except ValueError:
            max_articles = 3

    report = run_discover_and_verify(portal, interests, max_articles=max_articles)
    print("\n================= 发现与验证报告 =================\n")
    print(report)

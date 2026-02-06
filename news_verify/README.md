# news_verify 包

新闻发现与事实核查多智能体逻辑，统一入口与层次结构说明。

## 包结构

```
news_verify/
├── __init__.py              # 对外导出：run_discover_and_verify, run_news_fact_check, llm, MAX_CONTENT_CHARS_FOR_LLM
├── llm.py                   # LLM 配置（ModelScope/OpenAI 兼容）
├── utils.py                 # 通用工具：safe_slug, kickoff_with_retry
├── tools/
│   ├── __init__.py
│   ├── crawl.py             # 门户/文章爬虫：PortalCrawlerTool, ArticleCrawlerTool
│   └── verify.py            # 验证工具：FileReadTool, SerperSearchTool
├── agents_news.py           # 新闻侧智能体：兴趣抽取、选新闻、抓文章、事实核查、写报告
├── agents_verify.py         # 验证侧智能体：分析新闻、执行 Serper 验证
├── tasks_news.py            # 新闻侧任务：interest_task, news_select_task, article_collect_task, fact_check_task, report_task
├── tasks_verify.py          # 验证侧任务工厂：make_identify_claims_task, make_*_search_queries_task, make_compile_verification_plan_task, make_verify_claims_task
├── pipeline_discover_verify.py  # 流程：发现新闻 → 逐篇验证（计划+Serper）→ 汇总报告
└── pipeline_fact_check.py   # 流程：发现新闻 → 逐篇事实核查（Serper）→ 汇总报告
```

## 依赖层次

- **llm**、**utils**、**tools**：无包内依赖，可单独使用。
- **agents_news**：依赖 llm、tools.crawl、tools.verify（serper_search_tool / SerperDevTool）。
- **agents_verify**：依赖 llm、tools.verify。
- **tasks_news**：依赖 agents_news、tools.crawl、agents_news.serper_tool。
- **tasks_verify**：依赖 agents_verify。
- **pipeline_discover_verify**：依赖 llm、utils、agents_news、agents_verify、tasks_news、tasks_verify、tools.crawl。
- **pipeline_fact_check**：依赖 llm、utils、agents_news、tasks_news、tools.crawl。

## 入口脚本（根目录）

- `news_discover_verify_crew.py`：仅导入 `run_discover_and_verify` 并作为命令行入口。
- `news_fact_check_crew.py`：仅导入 `run_news_fact_check` 并作为命令行入口。
- `web_app/app.py`：从 `news_verify` 导入 `run_discover_and_verify` 驱动 Web 流程。

## 使用

```python
from news_verify import run_discover_and_verify, run_news_fact_check

# 发现 + 逐篇验证（计划+Serper）+ 汇总
report = run_discover_and_verify(
    "https://apnews.com/",
    "我对特朗普对外政策比较感兴趣",
    max_articles=3,
    on_event=my_callback,  # 可选，用于 UI 流式展示
)

# 发现 + 逐篇事实核查（Serper）+ 汇总
report = run_news_fact_check(
    "https://news.yahoo.com/",
    "我对人工智能、科技比较感兴趣",
    articles_dir="data/articles",
    reports_dir="reports",
)
```

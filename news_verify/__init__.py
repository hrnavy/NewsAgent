"""
新闻发现与事实核查多智能体包。

顶层入口：
- run_discover_and_verify: 发现新闻 → 逐篇验证（计划+Serper）→ 汇总报告
- run_news_fact_check: 发现新闻 → 逐篇事实核查（Serper）→ 汇总报告
"""
from news_verify.llm import llm, MAX_CONTENT_CHARS_FOR_LLM
from news_verify.pipeline_discover_verify import run_discover_and_verify
from news_verify.pipeline_fact_check import run_news_fact_check

__all__ = [
    "run_discover_and_verify",
    "run_news_fact_check",
    "llm",
    "MAX_CONTENT_CHARS_FOR_LLM",
]

"""
多智能体流程：发现新闻 → 逐篇事实核查（Serper）→ 汇总报告。
"""
import os
import json
import re
import datetime as dt
from typing import Any

from crewai import Crew

from news_verify.llm import llm, MAX_CONTENT_CHARS_FOR_LLM
from news_verify.utils import safe_slug, crew_output_string, extract_json_array
from news_verify.agents_news import (
    interest_extractor_agent,
    news_selector_agent,
    article_saver_agent,
    fact_checker_agent,
    report_writer_agent,
)
from news_verify.tasks_news import (
    interest_task,
    news_select_task,
    article_collect_task,
    fact_check_task,
    report_task,
)
from news_verify.tools.crawl import portal_crawler_tool, article_crawler_tool


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def run_news_fact_check(
    portal_url: str,
    user_interest_desc: str,
    *,
    articles_dir: str = "data/articles",
    fact_checks_dir: str = "data/fact_checks",
    reports_dir: str = "reports",
) -> str:
    """
    高层封装：
    1. 提取兴趣标签
    2. 从门户主页筛选新闻
    3. 抓取新闻全文
    4. 对每篇新闻做事实核查
    5. 汇总并生成报告（返回 Markdown 字符串）
    """
    articles_dir = _ensure_dir(articles_dir)
    fact_checks_dir = _ensure_dir(fact_checks_dir)
    reports_dir = _ensure_dir(reports_dir)

    # 1. 兴趣抽取
    interest_crew = Crew(
        agents=[interest_extractor_agent],
        tasks=[interest_task],
        verbose=True,
        llm=llm,
    )
    interest_result = interest_crew.kickoff(
        inputs={"user_interest_desc": user_interest_desc}
    )
    interest_json = str(interest_result).strip()
    json_match = re.search(r'\{[^}]*"interests"[^}]*\}', interest_json)
    if json_match:
        interest_json = json_match.group(0)

    # 2. 选新闻
    news_select_crew = Crew(
        agents=[news_selector_agent],
        tasks=[news_select_task],
        verbose=True,
        llm=llm,
    )
    selected_news_result = news_select_crew.kickoff(
        inputs={
            "portal_url": portal_url,
            "interest_json": interest_json,
            "user_interest_desc": user_interest_desc,
        }
    )
    selected_news_json = crew_output_string(selected_news_result)
    selected_news_json = extract_json_array(selected_news_json, fix_unescaped_newlines=True)

    try:
        selected_list = json.loads(selected_news_json)
    except json.JSONDecodeError:
        return f"新闻筛选结果无法解析为 JSON：\n\n{selected_news_json}"

    if not selected_list:
        raw_portal = portal_crawler_tool._run(portal_url)
        try:
            portal_data = json.loads(raw_portal)
            candidates = portal_data.get("items", [])
            selected_list = candidates[:5]
        except Exception:
            selected_list = []
        if not selected_list:
            return "未获取到任何候选新闻（门户抓取或筛选结果为空），请换一个门户 URL 或兴趣再试。"

    # 3. 抓取正文
    raw_crawl = article_crawler_tool._run(selected_news_json)
    try:
        crawl_by_url = json.loads(raw_crawl)
    except json.JSONDecodeError:
        return f"抓取结果无法解析：\n\n{raw_crawl}"

    articles = []
    for item in selected_list:
        url = item.get("url", "")
        title = item.get("title", "") or ""
        if not url:
            continue
        entry = crawl_by_url.get(url) or {}
        content_full = entry.get("markdown", "") or entry.get("content", "") or ""
        if entry.get("error"):
            content_full = f"[抓取失败: {entry['error']}]"
        title = title or entry.get("title", "") or url
        content_for_llm = content_full[:MAX_CONTENT_CHARS_FOR_LLM]
        if len(content_full) > MAX_CONTENT_CHARS_FOR_LLM:
            content_for_llm += "\n\n[正文已截断，仅用于事实核查]"
        articles.append({
            "title": title,
            "url": url,
            "content": content_for_llm,
            "_content_full": content_full,
        })

    fact_results = []
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存抓取到的新闻
    saved_articles = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title") or f"article_{idx}"
        url = article.get("url", "")
        content_full = article.get("_content_full", "") or article.get("content", "")
        slug = safe_slug(title)
        article_path = os.path.join(articles_dir, f"{ts}_{idx:02d}_{slug}.md")
        md = (
            f"# {title}\n\n"
            f"- Source: {url}\n"
            f"- CrawledAt: {ts}\n\n"
            f"---\n\n"
            f"{content_full}\n"
        )
        _write_text(article_path, md)
        saved_articles.append({
            "title": title,
            "url": url,
            "content": article.get("content", ""),
            "saved_path": article_path,
        })

    # 4. 对每篇文章做事实核查
    fact_check_crew = Crew(
        agents=[fact_checker_agent],
        tasks=[fact_check_task],
        verbose=True,
        llm=llm,
    )

    for idx, article in enumerate(saved_articles, start=1):
        article_json = json.dumps(article, ensure_ascii=False)
        result = fact_check_crew.kickoff(inputs={"article_json": article_json})
        result_str = str(result).strip()

        json_obj_match = re.search(r'\{.*\}', result_str, re.DOTALL)
        if json_obj_match:
            result_str = json_obj_match.group(0)

        try:
            parsed = json.loads(result_str)
        except json.JSONDecodeError:
            parsed = {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "error": "fact_check_output_not_json",
                "raw": result_str,
            }

        slug = safe_slug(article.get("title") or f"article_{idx}")
        fact_path = os.path.join(fact_checks_dir, f"{ts}_{idx:02d}_{slug}.json")
        _write_json(fact_path, parsed)
        parsed["_saved_path"] = fact_path
        parsed["_article_saved_path"] = article.get("saved_path")
        fact_results.append(parsed)

    fact_results_json = json.dumps(fact_results, ensure_ascii=False)

    # 5. 生成汇总报告
    report_crew = Crew(
        agents=[report_writer_agent],
        tasks=[report_task],
        verbose=True,
        llm=llm,
    )
    report_result = report_crew.kickoff(
        inputs={"fact_check_results_json": fact_results_json}
    )
    report_markdown = str(report_result)

    report_path = os.path.join(reports_dir, f"fact_check_report_{ts}.md")
    _write_text(report_path, report_markdown)

    report_with_header = (
        f"> Report saved to: `{report_path}`\n"
        f"> Articles saved to: `{os.path.abspath(articles_dir)}`\n"
        f"> Fact checks saved to: `{os.path.abspath(fact_checks_dir)}`\n\n"
        + report_markdown
    )

    return report_with_header

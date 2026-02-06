"""
多智能体流程：发现新闻 → 逐篇验证（计划 + Serper）→ 汇总报告。
on_event 可选，用于 Web UI 流式展示。
"""
import os
import json
import re
import datetime as dt
from pathlib import Path
from typing import List, Any, Optional, Callable

from crewai import Crew, Process

from news_verify.llm import llm, MAX_CONTENT_CHARS_FOR_LLM
from news_verify.utils import safe_slug, kickoff_with_retry, crew_output_string, extract_json_array
from news_verify.agents_news import (
    interest_extractor_agent,
    news_selector_agent,
    article_saver_agent,
    report_writer_agent,
)
from news_verify.agents_verify import analyze_news_agent, verify_claims_agent
from news_verify.tasks_news import interest_task, news_select_task, report_task
from news_verify.tasks_verify import (
    make_identify_claims_task,
    make_create_search_queries_task,
    make_compile_verification_plan_task,
    make_verify_claims_task,
)
from news_verify.tools.crawl import portal_crawler_tool, article_crawler_tool


def _clean_article_with_llm(raw_content: str, title: str, url: str) -> str:
    """用 LLM 清洗抓取原文：仅保留正文，去掉广告、导航等。"""
    raw_content = (raw_content or "").strip()
    if not raw_content:
        return ""

    from openai import OpenAI

    api_key = os.getenv("MODELSCOPE_API_KEY")
    base_url = os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
    model = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")
    if not api_key:
        return raw_content

    client = OpenAI(api_key=api_key, base_url=base_url)
    system = (
        "You are a news editor. Your task: given raw scraped webpage content, output ONLY the main news article body. "
        "Remove: ads, 'related news', 'other stories', navigation, footers, cookie banners, sidebars, author bios, comments. "
        "Output clean markdown (title, paragraphs, no extra sections). No preamble or explanation."
    )
    user = f"Title: {title}\nURL: {url}\n\nRaw content:\n{raw_content}"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=21000,
        )
        cleaned = (resp.choices[0].message.content or "").strip()
        if cleaned:
            return cleaned
    except Exception:
        pass
    return raw_content


def run_discover_and_verify(
    portal_url: str,
    user_interest_desc: str,
    *,
    max_articles: int = 3,
    reports_dir: str = "reports",
    on_event: Optional[Callable[[str, str, str, Any], None]] = None,
) -> str:
    """
    多智能体流程：寻找新闻 → 逐篇验证真假 → 汇总报告。
    on_event(step_id, status, message, detail) 可选，用于 UI 流式展示。
    """
    def emit(step_id: str, status: str, message: str, detail: Any = None) -> None:
        if on_event:
            try:
                on_event(step_id, status, message, detail)
            except Exception:
                pass

    reports_base = Path(reports_dir)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = reports_base / f"discover_verify_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir_str = str(run_dir).replace("\\", "/")
    emit("run_dir", "info", "报告目录已创建", {"run_dir": run_dir_str})

    # ---------- 阶段 1：发现新闻 ----------
    emit("log", "info", "连接推理模型", None)
    emit("interest_extract", "start", "提取用户兴趣标签", None)
    interest_crew = Crew(
        agents=[interest_extractor_agent],
        tasks=[interest_task],
        verbose=True,
        llm=llm,
    )
    interest_result = kickoff_with_retry(interest_crew, {"user_interest_desc": user_interest_desc})
    interest_json = str(interest_result).strip()
    json_match = re.search(r'\{[^}]*"interests"[^}]*\}', interest_json)
    if json_match:
        interest_json = json_match.group(0)
    emit("interest_extract", "done", "兴趣标签已生成", interest_json)

    emit("log", "info", "调用门户爬虫获取候选链接", None)
    emit("news_select", "start", "调用 LLM 筛选相关新闻", None)
    news_select_crew = Crew(
        agents=[news_selector_agent],
        tasks=[news_select_task],
        verbose=True,
        llm=llm,
    )
    selected_news_result = kickoff_with_retry(
        news_select_crew,
        {
            "portal_url": portal_url,
            "interest_json": interest_json,
            "user_interest_desc": user_interest_desc,
        },
    )
    selected_news_json = crew_output_string(selected_news_result)
    selected_news_json = extract_json_array(selected_news_json, fix_unescaped_newlines=True)
    emit("news_select", "done", "已筛选候选新闻", {"tool_output": selected_news_json[:8000]})

    try:
        selected_list = json.loads(selected_news_json)
    except json.JSONDecodeError:
        emit("news_select", "error", "筛选结果非 JSON", selected_news_json)
        return f"新闻筛选结果无法解析为 JSON：\n\n{selected_news_json}"

    if not selected_list:
        raw_portal = portal_crawler_tool._run(portal_url)
        try:
            portal_data = json.loads(raw_portal)
            candidates = portal_data.get("items", [])
            selected_list = candidates[: max_articles + 2]
        except Exception:
            selected_list = []
        if not selected_list and "/" in portal_url.rstrip("/").replace("https://", "").replace("http://", ""):
            from urllib.parse import urlparse
            parsed = urlparse(portal_url)
            fallback_url = f"{parsed.scheme or 'https'}://{parsed.netloc}/"
            if fallback_url != portal_url.rstrip("/") + "/":
                raw_portal = portal_crawler_tool._run(fallback_url)
                try:
                    portal_data = json.loads(raw_portal)
                    candidates = portal_data.get("items", [])
                    selected_list = candidates[: max_articles + 2]
                except Exception:
                    pass
        if not selected_list:
            return "未获取到任何候选新闻（门户抓取返回空）。可尝试换用门户首页 URL，如 https://www.reuters.com/ 或 https://news.yahoo.com/"

    selected_list = selected_list[:max_articles]
    emit("log", "info", "调用文章爬虫抓取正文", None)
    emit("article_crawl", "start", f"抓取 {len(selected_list)} 篇文章正文", None)
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
            content_for_llm += "\n\n[正文已截断]"
        articles.append({
            "title": title,
            "url": url,
            "content": content_for_llm,
            "_content_full": content_full,
        })

    if not articles:
        emit("article_crawl", "error", "未抓取到正文", None)
        return "未成功抓取到任何文章正文，请检查门户或网络。"
    emit("article_crawl", "done", f"已抓取 {len(articles)} 篇", None)

    # ---------- 阶段 2：逐篇验证 ----------
    verification_report_paths: List[str] = []

    for idx, article in enumerate(articles, start=1):
        slug = safe_slug(article.get("title") or f"article_{idx}")
        emit("log", "info", "调用 LLM 清洗正文", None)
        emit(f"article_{idx}_clean", "start", f"清洗正文：{article.get('title', '')[:40]}…", None)
        article_dir = run_dir / f"article_{idx:02d}_{slug}"
        article_dir.mkdir(parents=True, exist_ok=True)

        extracted_path = article_dir / "extracted_news.md"
        raw_body = article.get("_content_full", article.get("content", ""))
        cleaned_body = _clean_article_with_llm(
            raw_body,
            article.get("title", ""),
            article.get("url", ""),
        )
        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(f"# {article['title']}\n\n")
            f.write(f"- Source: {article['url']}\n\n---\n\n")
            f.write(cleaned_body)
        rel = str(extracted_path).replace("\\", "/")
        emit(f"article_{idx}_clean", "done", "正文已清洗", {"files": [{"path": rel, "label": "extracted_news.md"}]})

        emit("log", "info", "调用 LLM 识别声明与生成核查计划", None)
        emit(f"article_{idx}_analyze", "start", "识别关键声明并生成核查计划", None)
        claims_path = article_dir / "identified_claims.json"
        queries_path = article_dir / "search_queries.json"
        plan_path = article_dir / "verification_plan.md"
        report_path = article_dir / "verification_report.md"

        analyze_t1 = make_identify_claims_task()
        analyze_t1.output_file = str(claims_path)
        analyze_t2 = make_create_search_queries_task()
        analyze_t2.output_file = str(queries_path)
        analyze_t3 = make_compile_verification_plan_task()
        analyze_t3.output_file = str(plan_path)

        analyze_crew = Crew(
            agents=[analyze_news_agent],
            tasks=[analyze_t1, analyze_t2, analyze_t3],
            process=Process.sequential,
            verbose=True,
            llm=llm,
        )
        kickoff_with_retry(analyze_crew, {
            "extracted_news_path": str(extracted_path),
            "identified_claims_path": str(claims_path),
            "search_queries_path": str(queries_path),
        })
        rels = [str(p).replace("\\", "/") for p in (claims_path, queries_path, plan_path)]
        emit(f"article_{idx}_analyze", "done", "核查计划已生成", {"files": [{"path": rels[0], "label": "identified_claims.json"}, {"path": rels[1], "label": "search_queries.json"}, {"path": rels[2], "label": "verification_plan.md"}]})

        verify_task = make_verify_claims_task()
        verify_task.output_file = str(report_path)
        verify_crew = Crew(
            agents=[verify_claims_agent],
            tasks=[verify_task],
            process=Process.sequential,
            verbose=True,
            llm=llm,
        )
        emit("log", "info", "调用 Serper API 搜索验证声明", None)
        emit(f"article_{idx}_verify", "start", "执行搜索验证声明", None)
        kickoff_with_retry(verify_crew, {"verification_plan_path": str(plan_path)})
        rel_report = str(report_path).replace("\\", "/")
        emit(f"article_{idx}_verify", "done", "该篇验证完成", {"files": [{"path": rel_report, "label": "verification_report.md"}]})

        verification_report_paths.append(str(report_path))

    # ---------- 阶段 3：汇总报告 ----------
    emit("log", "info", "调用 LLM 汇总报告", None)
    emit("summary", "start", "汇总验证报告", None)
    fact_check_results = []
    for idx, (article, p) in enumerate(zip(articles, verification_report_paths), start=1):
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"[无法读取 {p}: {e}]"
        fact_check_results.append({
            "title": article.get("title", f"Article {idx}"),
            "url": article.get("url", ""),
            "verification_report": content,
        })
    fact_check_results_json = json.dumps(fact_check_results, ensure_ascii=False)

    summary_crew = Crew(
        agents=[report_writer_agent],
        tasks=[report_task],
        verbose=True,
        llm=llm,
    )
    summary_result = kickoff_with_retry(summary_crew, {"fact_check_results_json": fact_check_results_json})
    summary_md = str(summary_result)

    summary_path = run_dir / "summary_report.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    header = (
        f"> 发现与验证报告已保存：`{summary_path}`\n"
        f"> 各篇验证详情目录：`{run_dir}`\n\n"
    )
    rel_summary = str(summary_path).replace("\\", "/")
    emit("summary", "done", "报告已生成", {"files": [{"path": rel_summary, "label": "summary_report.md"}]})
    emit("complete", "done", "流程结束", {"run_dir": str(run_dir), "summary_path": str(summary_path), "files": [{"path": rel_summary, "label": "summary_report.md"}]})
    return header + summary_md

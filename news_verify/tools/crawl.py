"""门户与文章爬虫工具（Crawl4AI）。"""
import asyncio
import json
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


class PortalCrawlerTool(BaseTool):
    name: str = "Portal Crawler"
    description: str = (
        "Given a news portal homepage URL, crawl it and extract candidate news links "
        "with their titles and short snippets. Always return a JSON list of items."
    )

    def _run(self, portal_url: str) -> str:
        async def crawl() -> Dict[str, Any]:
            browser_config = BrowserConfig()
            run_config = CrawlerRunConfig(
                page_timeout=90_000,
                wait_until="commit",
            )
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=portal_url, config=run_config)
                html = result.html or ""
                soup = BeautifulSoup(html, "html.parser")

                seen: set = set()
                items: List[Dict[str, str]] = []

                for a in soup.find_all("a", href=True):
                    href = (a["href"] or "").strip()
                    text = a.get_text(strip=True)
                    if not text or len(text) < 3:
                        continue
                    full_url = href
                    if full_url.startswith("//"):
                        full_url = "https:" + full_url
                    elif full_url.startswith("/"):
                        full_url = urljoin(portal_url, full_url)
                    if not full_url.startswith("http"):
                        continue
                    parsed = urlparse(full_url)
                    path = (parsed.path or "").lower()
                    if full_url.rstrip("/") == portal_url.rstrip("/"):
                        continue
                    if any(skip in path for skip in ["/login", "/signup", "/tag/", "/author/", "/subscribe"]):
                        continue
                    path_segments = [s for s in path.split("/") if s]
                    is_article = (
                        "/article" in path
                        or "/news" in path
                        or "/story" in path
                        or "/202" in path
                        or "detail" in path
                        or (len(path) > 15 and ("/" in path[1:] or path.count("-") >= 2))
                        or (len(path_segments) >= 2 and len(path) > 8)
                    )
                    if not is_article:
                        continue
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    items.append({"title": text[:200], "url": full_url})

                return {"portal_url": portal_url, "items": items}

        data = asyncio.run(crawl())
        return json.dumps(data, ensure_ascii=False, indent=2)


class ArticleCrawlerTool(BaseTool):
    name: str = "Article Crawler"
    description: str = "Given a list of article URLs, crawl each page and return full text content. Input/Output are JSON."

    def _run(self, articles_json: str) -> str:
        try:
            articles: List[Dict[str, Any]] = json.loads(articles_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input for articles"}, ensure_ascii=False)

        async def crawl_many(urls: List[str]) -> Dict[str, Any]:
            browser_config = BrowserConfig()
            run_config = CrawlerRunConfig(
                page_timeout=90_000,
                wait_until="commit",
            )
            results: Dict[str, Any] = {}
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for url in urls:
                    try:
                        r = await crawler.arun(url=url, config=run_config)
                        if r is None:
                            results[url] = {"url": url, "error": "crawler returned None"}
                            continue
                        md = getattr(r, "markdown", None) or ""
                        meta = getattr(r, "metadata", None)
                        title = ""
                        if isinstance(meta, dict):
                            title = meta.get("title", "") or ""
                        results[url] = {"url": url, "markdown": md, "title": title}
                    except BaseException as e:
                        results[url] = {"url": url, "error": str(e)}
            return results

        urls = [a["url"] for a in articles if "url" in a]
        data = asyncio.run(crawl_many(urls))
        return json.dumps(data, ensure_ascii=False, indent=2)


portal_crawler_tool = PortalCrawlerTool()
article_crawler_tool = ArticleCrawlerTool()

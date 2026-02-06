"""新闻发现与事实核查流程中的新闻侧任务。"""
from crewai import Task

from news_verify.agents_news import (
    interest_extractor_agent,
    news_selector_agent,
    article_saver_agent,
    fact_checker_agent,
    report_writer_agent,
)
from news_verify.tools.crawl import portal_crawler_tool, article_crawler_tool
from news_verify.agents_news import serper_tool

interest_task = Task(
    description="""
        用户兴趣描述：{user_interest_desc}

        **重要**：你必须根据上述「用户兴趣描述」的实际内容提取兴趣标签，不要使用其他示例。
        例如用户说「特朗普对外政策」则应提取：特朗普、美国外交、贸易政策、关税 等；用户说「人工智能」则提取 AI、科技 等。

        你的任务：
        1. 只根据上面的「用户兴趣描述」理解真实兴趣
        2. 提取 3-10 个兴趣标签（领域、主题、人物、公司、国家/地区等）
        3. 输出唯一一个 JSON：{{"interests": ["标签1", "标签2", ...]}}
    """,
    expected_output="仅一个 JSON 字符串 {\"interests\": [...]}，标签必须来自用户兴趣描述。",
    agent=interest_extractor_agent,
)

news_select_task = Task(
    description="""
        你会得到：
        1. 门户网站主页 URL: {portal_url}
        2. 用户兴趣标签（仅供参考）: {interest_json}
        3. **用户亲口描述的兴趣**：{user_interest_desc}

        步骤：
        1. 使用 Portal Crawler 工具抓取该门户主页，获得候选新闻列表（每条有 title、url）。
        2. **用你的理解能力筛选，不要用关键词匹配**：
           - 阅读每条新闻的标题，理解其主题、涉及的人物/事件/领域；
           - 结合用户描述的兴趣（例如「俄乌」= 俄罗斯与乌克兰局势、战争、外交等），选出语义上最相关的 3-10 条；
           - 不要求标题里出现用户说的字眼，只要主题相关即可（如用户关心俄乌，选国际冲突、北约、东欧局势等也可）。
        3. **禁止返回空数组**：若没有明显相关报道，也从候选中按「与用户兴趣最接近」选出至少 3 条。

        输出：仅一个 JSON 数组，每项含 title、url，不要加解释。
    """,
    expected_output="一个非空的 JSON 数组字符串，形如 [{\"title\": \"...\", \"url\": \"...\"}, ...]，至少 1 条。",
    agent=news_selector_agent,
    tools=[portal_crawler_tool],
)

article_collect_task = Task(
    description="""
        你会得到上一任务筛选好的文章列表 JSON：{selected_news_json}

        步骤：
        1. 使用 Article Crawler 工具对其中每个 url 进行抓取
        2. 对每篇文章提取：
           - title: 标题（可以使用页面 metadata 或正文首行）
           - url
           - content: 主要正文内容（markdown 即可）
        3. 以 JSON 数组形式输出所有文章：
           [
             { "title": "...", "url": "...", "content": "..." },
             ...
           ]
    """,
    expected_output="一个 JSON 数组字符串，包含所有已抓取文章的 title/url/content。",
    agent=article_saver_agent,
    tools=[article_crawler_tool],
)

fact_check_task = Task(
    description="""
        你会得到一篇新闻文章的结构化内容 JSON：{article_json}

        你的任务：
        1. 从文章中提取 3-8 条最关键的「事实性陈述」，例如数字、时间、事件、人物关系、因果关系等
        2. 对每一条陈述，使用 Serper 搜索工具在互联网上查找多个来源
        3. 判断该陈述是：
           - 正确（大部分可靠来源支持）
           - 部分正确 / 有争议（不同来源说法不一致）
           - 错误 / 过时（主流来源否认或已被更新）
        4. 为每条陈述整理：
           - claim: 原始陈述
           - verdict: 结论 (TRUE / PARTIALLY_TRUE / FALSE / UNCERTAIN)
           - evidence: 1-3 条主要证据的简要说明和对应链接

        输出格式：
        - 仅输出 JSON，形如：
          {{
            "title": "...",
            "url": "...",
            "checks": [
              {{
                "claim": "...",
                "verdict": "TRUE",
                "evidence": [
                  {{"source": "xxx", "url": "https://...", "note": "..." }}
                ]
              }},
              ...
            ]
          }}
    """,
    expected_output="一个 JSON 对象字符串，包含 title/url 和 checks 数组。",
    agent=fact_checker_agent,
    tools=[serper_tool],
)

report_task = Task(
    description="""
        你会得到若干篇文章的事实核查结果 JSON 数组：{fact_check_results_json}

        请用中文撰写一份结构化的事实核查报告，面向普通读者，包含：
        1. 简短的总览：本次共核查了几篇新闻，大致结论如何
        2. 按文章分组：
           - 文章标题 + 链接
           - 一段简要摘要（你可以根据核查结果反推大致主题）
           - 列出每条被核查的陈述：
             * 原始陈述
             * 结论（正确 / 部分正确 / 错误 / 存疑）
             * 一两句说明（不要列出太多技术细节）
        3. 总结部分：
           - 对整体信息可靠性的评价
           - 对读者的提醒（例如：哪些话题目前争议较大，需要持续关注）

        报告请使用 Markdown 格式输出，适合直接发布到网页或笔记工具。
    """,
    expected_output="一份结构清晰的中文 Markdown 报告。",
    agent=report_writer_agent,
)

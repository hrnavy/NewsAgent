"""新闻发现与事实核查流程中的新闻侧智能体。"""
from crewai import Agent

from news_verify.llm import llm
from news_verify.tools.crawl import portal_crawler_tool, article_crawler_tool
from news_verify.tools.verify import serper_search_tool

# SerperDevTool 用于 fact_check 流程（逐篇事实核查）
try:
    from crewai_tools import SerperDevTool
    serper_tool = SerperDevTool()
except Exception:
    serper_tool = serper_search_tool  # 无 crewai_tools 时退化为自定义 SerperSearchTool

interest_extractor_agent = Agent(
    role="User Interest Analyzer",
    goal=(
        "从用户的一段兴趣描述中抽取清晰的兴趣关键词和主题，"
        "用于在新闻门户站点主页中过滤出对用户最有价值的新闻。"
    ),
    backstory=(
        "你擅长从用户的自然语言描述中识别出关注的领域，比如科技、财经、体育、地区、公司名等，"
        "并将其整理为结构化的兴趣标签。"
    ),
    llm=llm,
    verbose=True,
)

news_selector_agent = Agent(
    role="News Selector",
    goal=(
        "根据用户兴趣描述，用你的理解能力从候选新闻中选出语义上最相关的若干篇；"
        "不依赖关键词匹配，而是理解标题和用户兴趣的含义后再筛选。"
    ),
    backstory=(
        "你是一名资深新闻编辑，擅长通过理解标题和主题（而非简单关键词）判断新闻与读者兴趣的相关性，"
        "能从大量候选中挑出语义上最相关、最有价值的几篇。"
    ),
    tools=[portal_crawler_tool],
    llm=llm,
    verbose=True,
)

article_saver_agent = Agent(
    role="Article Collector",
    goal="抓取并保存选中的新闻全文，以便后续事实核查。",
    backstory="你负责把所有选中的新闻页面抓取下来，并输出结构化的文章内容（标题、正文等）。",
    tools=[article_crawler_tool],
    llm=llm,
    verbose=True,
)

fact_checker_agent = Agent(
    role="Fact Check Analyst",
    goal=(
        "对一篇新闻中的关键事实进行核查，利用网络搜索验证各个重要声明是否准确、过时或有争议。"
    ),
    backstory=(
        "你是一名专业事实核查员，习惯逐条拆解新闻中的事实性陈述，"
        "通过多个可靠来源交叉验证，并明确给出每条结论。"
    ),
    tools=[serper_tool],
    llm=llm,
    verbose=True,
)

report_writer_agent = Agent(
    role="Fact Check Reporter",
    goal="根据事实核查结果，撰写一份给终端用户看的中文验证报告，结构清晰、结论明确。",
    backstory="你是一名调查记者，擅长把复杂的核查过程总结为通俗易懂的报告。",
    llm=llm,
    verbose=True,
)

"""验证阶段智能体：分析新闻、生成核查计划、执行 Serper 验证。"""
from crewai import Agent

from news_verify.llm import llm
from news_verify.tools.verify import file_read_tool, serper_search_tool

analyze_news_agent = Agent(
    role="News Verification Strategist",
    goal="Analyze news content and create a verification plan with specific search queries to validate claims",
    backstory=(
        "You are an expert fact-checker and verification strategist. You excel at analyzing news articles "
        "and identifying the most critical claims that need verification. You are skilled at crafting "
        "precise search queries that can effectively validate or debunk specific claims. "
        "You ALWAYS output ONLY the final results (JSON or markdown). Never include thoughts or explanations."
    ),
    tools=[file_read_tool],
    llm=llm,
    verbose=False,
)

verify_claims_agent = Agent(
    role="Claim Verification Specialist",
    goal="Execute web searches using Serper API to verify claims and gather evidence from multiple sources",
    backstory=(
        "You are a meticulous fact-checker with expertise in web research and evidence gathering. "
        "You know how to craft effective search queries and evaluate the credibility of sources. "
        "You ALWAYS output ONLY the final results (JSON and markdown). Never include thoughts or explanations."
    ),
    tools=[serper_search_tool, file_read_tool],
    llm=llm,
    verbose=False,
)

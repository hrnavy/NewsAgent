"""验证阶段任务工厂：识别声明、生成搜索查询、编译核查计划、执行验证。"""
from crewai import Task

from news_verify.agents_verify import analyze_news_agent, verify_claims_agent


def make_identify_claims_task():
    return Task(
        description="""
    Read the extracted news content from {extracted_news_path} and identify the critical claims that need verification.

    Your task:
    1. Use the File Reader tool to read the complete news content from the file path: {extracted_news_path}
    2. Identify the main claims and assertions in the article
    3. Extract key entities (people, organizations, locations, dates)
    4. Prioritize claims based on: importance to the overall story, verifiability, potential impact if false
    5. Select the top 5-8 most critical claims for verification

    For each claim, provide: Exact statement, Why it needs verification, Priority level (High/Medium/Low)

    IMPORTANT: Your final answer MUST be ONLY the JSON object. Do NOT include any thoughts, explanations, or additional text.
    """,
        expected_output="Output ONLY a JSON object with news_summary and critical_claims array. Save to the specified file.",
        agent=analyze_news_agent,
    )


def make_create_search_queries_task():
    return Task(
        description="""
    Read the identified claims from {identified_claims_path} and create search queries for each claim.

    Your task:
    1. Use the File Reader tool to read the claims from the file path: {identified_claims_path}
    2. For each claim, design 2-3 specific search queries that can find official sources, independent news, expert opinions, or contradictory evidence.

    For each search query provide: Exact query string, What the query aims to find, Expected result type.

    IMPORTANT: Your final answer MUST be ONLY the JSON object. Do NOT include any thoughts, explanations, or additional text.
    """,
        expected_output="Output ONLY a JSON object with search_queries array. Save to the specified file.",
        agent=analyze_news_agent,
    )


def make_compile_verification_plan_task():
    return Task(
        description="""
    Read the identified claims from {identified_claims_path} and search queries from {search_queries_path} to compile a complete verification plan.

    Your task:
    1. Use the File Reader tool to read identified_claims.json from {identified_claims_path}
    2. Use the File Reader tool to read search_queries.json from {search_queries_path}
    3. Merge the data into a complete verification plan with verification strategy and success criteria
    4. Create a human-readable markdown report

    The final output should have TWO parts: PART 1 Complete JSON verification plan, PART 2 Human-readable markdown.
    IMPORTANT: Your final answer MUST contain ONLY these two parts. Do NOT include any thoughts, explanations, or additional text.
    """,
        expected_output="PART 1: JSON verification plan. PART 2: Human-readable markdown. Save to the specified file.",
        agent=analyze_news_agent,
    )


def make_verify_claims_task():
    return Task(
        description="""
    Read the verification plan from {verification_plan_path} and execute web searches using Serper API to verify the claims.

    Your task:
    1. Use the File Reader tool to read the verification_plan.md file from {verification_plan_path}
    2. Extract the JSON verification plan from the file content
    3. For each critical claim, execute the search queries using the serper_search tool
    4. Analyze the search results and evaluate the evidence to determine if each claim is:
       CONFIRMED, CONTRADICTED, AMBIGUOUS, or UNVERIFIED
    5. Document your findings with specific sources and evidence

    For each claim provide: Verification status, Evidence summary, Supporting sources, Confidence level, Caveats.

    IMPORTANT: Your output must be in TWO parts: PART 1 JSON Verification Results, PART 2 Human-Readable Markdown Report.
    """,
        expected_output="PART 1: JSON with verification_results. PART 2: Markdown verification report. Save to the specified file.",
        agent=verify_claims_agent,
    )

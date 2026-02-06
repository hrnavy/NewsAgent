import os
import json
import uuid
import asyncio

from typing import List, Dict, Any, Optional, Annotated, Type

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from crewai import Crew, Task, Agent, LLM
from crewai.tools import BaseTool

from tavily import TavilyClient
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

from bs4 import BeautifulSoup
import nest_asyncio

from maxim import Maxim, Config as MaximConfig
from maxim.logger import LoggerConfig
from maxim.logger.components.trace import TraceConfig
from maxim.logger import ToolCallConfig


nest_asyncio.apply()
load_dotenv()


# -----------------------------------------------------------------------------
# LLM CONFIG (ModelScope OpenAI-compatible endpoint)
# -----------------------------------------------------------------------------

MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY")
MODELSCOPE_BASE_URL = os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
MODELSCOPE_MODEL = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")

if not MODELSCOPE_API_KEY:
    raise RuntimeError("MODELSCOPE_API_KEY is not set. Please add it to your .env file.")

# CrewAI 内置 LLM，通过 litellm 走 OpenAI 协议到魔搭 ModelScope
llm = LLM(
    model=f"openai/{MODELSCOPE_MODEL}",
    api_key=MODELSCOPE_API_KEY,
    base_url=MODELSCOPE_BASE_URL,
    temperature=0.7,
)


# -----------------------------------------------------------------------------
# Maxim AI logger setup
# -----------------------------------------------------------------------------

MAXIM_API_KEY = os.getenv("MAXIM_API_KEY")
MAXIM_LOG_REPO_ID = os.getenv("MAXIM_LOG_REPO_ID")

maxim = None
logger = None

if MAXIM_API_KEY and MAXIM_LOG_REPO_ID:
    maxim = Maxim(MaximConfig(api_key=MAXIM_API_KEY))
    logger = maxim.logger(LoggerConfig(id=MAXIM_LOG_REPO_ID))


def create_trace(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Create a Maxim trace if logger is configured, otherwise return None."""
    if logger is None:
        return None
    trace = logger.trace(
        TraceConfig(
            id=str(uuid.uuid4()),
            name=name,
        )
    )
    if metadata:
        trace.event(
            id=str(uuid.uuid4()),
            name=f"{name}_event",
            metadata=metadata,
            tags={"event": name},
        )
    return trace


# -----------------------------------------------------------------------------
# Tavily Search Tool
# -----------------------------------------------------------------------------


class TavilySearchInput(BaseModel):
    query: Annotated[str, Field(description="The search query string")]
    max_results: Annotated[
        int, Field(description="Maximum number of results to return", ge=1, le=10)
    ] = 5
    search_depth: Annotated[
        str,
        Field(
            description="Search depth: 'basic' or 'advanced'",
        ),
    ] = "basic"


class TavilySearchTool(BaseTool):
    name: str = "Tavily Search"
    description: str = (
        "Use the Tavily API to perform a web search and get AI-curated results."
    )
    args_schema: Type[BaseModel] = TavilySearchInput
    client: Optional[Any] = None

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        key = api_key or os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set. Please add it to your .env file.")
        self.client = TavilyClient(api_key=key)

    def _run(self, query: str, max_results: int = 5, search_depth: str = "basic") -> str:
        if not self.client.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")

        try:
            response = self.client.search(
                query=query, max_results=max_results, search_depth=search_depth
            )

            output = self._process_response(response)

            # Send trace to Maxim if available
            if logger is not None:
                trace = create_trace("Tavily Search Trace")
                if trace is not None:
                    tool_call_config = ToolCallConfig(
                        id="tool_tavily_search",
                        name="Tavily Search",
                        description="Use the Tavily API to perform a web search and get AI-curated results.",
                        args={
                            "query": query,
                            "output": output,
                            "max_results": max_results,
                            "search_depth": search_depth,
                        },
                        tags={"tool": "tavily_search"},
                    )
                    trace.tool_call(tool_call_config)

            return output
        except Exception as e:
            return f"An error occurred while performing the search: {str(e)}"

    @staticmethod
    def _process_response(response: dict) -> str:
        if not response.get("results"):
            return "No results found."

        results = []
        for item in response["results"][:5]:
            title = item.get("title", "No title")
            content = item.get("content", "No content available")
            url = item.get("url", "No URL available")
            results.append(f"Title: {title}\nContent: {content}\nURL: {url}\n")

        return "\n".join(results)


tavily_search_tool = TavilySearchTool()


# -----------------------------------------------------------------------------
# Crawl4AI Web Crawler Tool
# -----------------------------------------------------------------------------


class WebCrawlerTool(BaseTool):
    name: str = "Web Crawler"
    description: str = "Crawls websites and extracts text and images."

    async def crawl_url(self, url: str) -> Dict[str, Any]:
        """Crawl a URL and extract its content."""
        print(f"Crawling URL: {url}")
        try:
            browser_config = BrowserConfig()
            run_config = CrawlerRunConfig()

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                # Extract images if available
                images = []
                soup = BeautifulSoup(result.markdown, "html.parser")
                for img in soup.find_all("img"):
                    if img.get("src"):
                        images.append(
                            {
                                "url": img.get("src"),
                                "alt": img.get("alt", ""),
                                "source_url": url,
                            }
                        )

                return {
                    "content": result.markdown,
                    "images": images,
                    "url": url,
                    "title": result.metadata.get("title", ""),
                }
        except Exception as e:
            return {"error": f"Failed to crawl {url}: {str(e)}", "url": url}

    def _run(self, urls: List[str]) -> Dict[str, Any]:
        """Implements the abstract _run method to integrate with CrewAI."""
        print(f"Crawling {len(urls)} URLs")
        results: Dict[str, Any] = {}

        async def process_urls():
            tasks = [self.crawl_url(url) for url in urls]
            return await asyncio.gather(*tasks)

        crawl_results = asyncio.run(process_urls())

        for result in crawl_results:
            url = result.get("url")
            if url:
                results[url] = result

        return results


web_crawler_tool = WebCrawlerTool()


# -----------------------------------------------------------------------------
# File Saver Tool
# -----------------------------------------------------------------------------


class FileSaverTool(BaseTool):
    name: str = "File Saver"
    description: str = "Saves a file to a specified local folder."

    def _run(self, file_content: str, save_folder: str, file_name: str) -> str:
        """Save the given content as a file in the specified folder."""
        try:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder, exist_ok=True)

            save_path = os.path.join(save_folder, file_name)

            with open(save_path, "w", encoding="utf-8") as file:
                file.write(file_content)

            return f"File saved at {save_path}"
        except Exception as e:
            return f"Error saving file: {str(e)}"


file_saver_tool = FileSaverTool()


# -----------------------------------------------------------------------------
# Agents
# -----------------------------------------------------------------------------


research_agent = Agent(
    role="Technical Researcher",
    goal=(
        "Search the web for information & blogs on the topic of {topic} provided by the user "
        "and extract the findings in a structured format."
    ),
    backstory=(
        "With over 10 years of experience in technical research, you can help users find the "
        "most relevant information on any topic."
    ),
    llm=llm,
    memory=True,
    verbose=True,
    tools=[tavily_search_tool, web_crawler_tool],
)

outline_agent = Agent(
    role="Tech Content Outlining Expert",
    goal="Create an outline for a technical blog post on the topic of {topic} provided by the user",
    backstory=(
        "With years of experience in creating technical content, you can help the user outline "
        "your blog post on any topic."
    ),
    memory=True,
    verbose=True,
    llm=llm,
    tools=[],
)

writer_agent = Agent(
    role="Tech Content Writer",
    goal="Write a technical blog post on the topic provided by the user",
    backstory=(
        "With years of experience in writing technical content, you can help the user create a "
        "high-quality blog post on any topic in markdown format. You can also include images in "
        "the blog post & code blocks."
    ),
    memory=True,
    verbose=True,
    llm=llm,
    tools=[],
)

critique_agent = Agent(
    role="Tech Content Critique Expert",
    goal="Critique a technical blog post written by the writer agent",
    backstory=(
        "With years of experience in critiquing technical content, you can help the user improve "
        "the quality of the blog post written by the writer agent."
    ),
    memory=True,
    verbose=True,
    llm=llm,
    tools=[],
)

revision_agent = Agent(
    role="Tech Content Revision Expert",
    goal="Revise a technical blog post based on the critique feedback provided by the critique agent",
    backstory=(
        "With years of experience in revising technical content, you can help the user implement "
        "the feedback provided by the critique agent to improve the quality of the blog post."
    ),
    memory=True,
    verbose=True,
    llm=llm,
    tools=[],
)

export_agent = Agent(
    role="Blog Exporter",
    goal=(
        "Export the final blog post in markdown format in the folder location provided by the user - {folder_path}"
    ),
    backstory=(
        "With experience in exporting technical content, you can help the user save the final "
        "blog post in markdown format to the specified folder location."
    ),
    memory=True,
    verbose=True,
    llm=llm,
    tools=[file_saver_tool],
)


# -----------------------------------------------------------------------------
# Tasks
# -----------------------------------------------------------------------------


research_task = Task(
    description="""
        Conduct a thorough research about the topic {topic} provided by the user.
        Make sure you find any interesting and relevant information given
        the current year is 2025. Use the Tavily Search tool to find the most 
        trending articles around the topic and use the Web Crawler tool to
        extract the content from the top articles.
    """,
    expected_output="""
        You should maintain a detailed raw content with all the findings. This should include the
        extracted content from the top articles.
    """,
    agent=research_agent,
)

outline_task = Task(
    description="""
        Create a structured outline for the technical blog post based on the research data.
        Ensure logical flow, clear sections, and coverage of all essential aspects. Plan for necessary headings, 
        tables & figures, and key points to be included in the blog post.

        The flow of every blog should be like this - 
        - Catcy Title
        - 2-3 line introduction / opening statement
        - Main Content (with subheadings)
        - Conclusion
        - References - Provide all the links that you have found during the research. 

        At any place if there is a need to draw an architecture diagram, you can put a note like this - 
        --- DIAGRAM HERE ---
        --- EXPLANATION OF DIAGRAM ---
    """,
    expected_output="""
        A markdown-styled hierarchical outline with headings, subheadings, and key points.
    """,
    agent=outline_agent,
)

writing_task = Task(
    description="""
        Write a detailed technical blog post in markdown format, integrating research insights.
        Keep the tone as first person and maintain a conversational style. The writer is young and enthusiastic 
        about technology but also knowledgeable in the field.
        Include code snippets and ensure clarity and depth. Use the outline as a guide to structure the content.
        Make sure to include required tables, comparisons and references. 
    """,
    expected_output="""
        A well-structured, easy-to-read technical blog post in markdown format.
    """,
    agent=writer_agent,
)

critique_task = Task(
    description="""
        Review the blog post critically, checking for technical accuracy, readability, and completeness.
        Provide constructive feedback with clear suggestions for improvement.
        Check if the content is not very boring to read and should be engaging. Necessary Tables and Figures should be included.
        The final article that is approved should be production ready, it can not have any place where we have
        used drafts or questions by LLM. It can just have the diagram placeholder.
    """,
    expected_output="""
        A markdown document with detailed feedback and proposed changes.
    """,
    agent=critique_agent,
)

revision_task = Task(
    description="""
        Revise the blog post based on critique feedback, ensuring higher quality and clarity.
    """,
    expected_output="""
        An improved version of the markdown blog post incorporating all necessary changes.
    """,
    agent=revision_agent,
)

export_task = Task(
    description="""
        Save the final blog post in markdown format to the specified folder location.
    """,
    expected_output="""
        A markdown file stored at the designated location in the same folder. 
    """,
    agent=export_agent,
)


# -----------------------------------------------------------------------------
# Crew definition
# -----------------------------------------------------------------------------


crew = Crew(
    agents=[
        research_agent,
        outline_agent,
        writer_agent,
        critique_agent,
        revision_agent,
        export_agent,
    ],
    tasks=[research_task, outline_task, writing_task, critique_task, revision_task, export_task],
    chat_llm=llm,
    manager_llm=llm,
    planning_llm=llm,
    function_calling_llm=llm,
    verbose=True,
)


def run_blog_crew(topic: str, folder_path: str) -> Any:
    inputs = {
        "topic": topic,
        "folder_path": folder_path,
    }

    trace = create_trace("CrewAI KickOff Event", metadata=inputs)
    if trace is not None:
        trace.event(
            id=str(uuid.uuid4()),
            name="CrewAI KickOff",
            metadata=inputs,
            tags={"event": "blog_crewai_kickoff"},
        )

    crew_output = crew.kickoff(inputs=inputs)
    return crew_output


if __name__ == "__main__":
    topic = input("请输入博客主题 (默认: CrewAI vs LangGraph for Building AI Agents): ").strip()
    if not topic:
        topic = "CrewAI vs LangGraph for Building AI Agents"

    folder_path = input("请输入保存 markdown 文件的文件夹路径 (默认: ./articles/crewai_vs_langgraph): ").strip()
    if not folder_path:
        folder_path = os.path.join(os.getcwd(), "articles", "crewai_vs_langgraph")

    print(f"\n使用主题: {topic}")
    print(f"保存路径: {folder_path}\n")

    result = run_blog_crew(topic, folder_path)

    # 简单打印输出（每个 task 的结果）
    print("\n" + "=" * 80)
    print("Crew 输出：")
    print("=" * 80 + "\n")
    print(result)


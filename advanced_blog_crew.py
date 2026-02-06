import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain_openai import ChatOpenAI
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.getenv("MODELSCOPE_API_KEY", "ms-dd2baa58-4a47-448b-93c6-1a14869a170e")
)

llm = ChatOpenAI(
    model=os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
    temperature=0.7,
    openai_api_key=os.getenv("MODELSCOPE_API_KEY", "ms-dd2baa58-4a47-448b-93c6-1a14869a170e"),
    openai_api_base=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
)

search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

researcher = Agent(
    role="Senior Research Analyst",
    goal="Conduct comprehensive research on the given topic using web search and scraping tools",
    backstory="""You are an expert researcher with access to powerful search and web scraping tools.
    You excel at finding relevant information, analyzing data, and synthesizing insights from multiple sources.
    Your research is thorough, accurate, and always up-to-date.""",
    tools=[search_tool, scrape_tool],
    verbose=True,
    allow_delegation=False,
    llm=llm
)

writer = Agent(
    role="Professional Tech Writer",
    goal="Transform research findings into engaging, well-structured blog content",
    backstory="""You are a skilled writer with a talent for making complex technical topics accessible and engaging.
    You have a deep understanding of content structure, SEO best practices, and audience engagement.
    Your writing is clear, compelling, and always tailored to the target audience.""",
    verbose=True,
    allow_delegation=True,
    llm=llm
)

editor = Agent(
    role="Senior Editor",
    goal="Polish and perfect the blog post for maximum impact and readability",
    backstory="""You are an experienced editor with a keen eye for detail and a passion for excellence.
    You ensure content is grammatically perfect, flows smoothly, and resonates with readers.
    You understand the importance of tone, style, and voice in creating memorable content.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

seo_specialist = Agent(
    role="SEO Specialist",
    goal="Optimize the blog post for search engines and discoverability",
    backstory="""You are an SEO expert who understands how to make content rank well in search results.
    You know how to optimize titles, meta descriptions, headings, and keywords without sacrificing readability.
    Your optimizations help content reach the right audience.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

research_task = Task(
    description="""Research the topic: {topic} comprehensively.
    
    Steps:
    1. Use search tools to find recent articles, news, and developments
    2. Scrape relevant websites for detailed information
    3. Identify key trends, statistics, and expert opinions
    4. Find real-world examples and case studies
    5. Gather information about tools, frameworks, and best practices
    
    Provide a detailed research summary with:
    - Key findings and insights
    - Supporting data and statistics
    - Expert quotes and opinions
    - Relevant examples and case studies
    - Current trends and future predictions""",
    expected_output="A comprehensive research report with findings, data, examples, and insights about the topic.",
    agent=researcher,
    tools=[search_tool, scrape_tool]
)

writing_task = Task(
    description="""Using the research findings, write an engaging blog post about {topic}.
    
    Structure:
    1. Catchy, SEO-friendly title
    2. Compelling introduction that hooks readers
    3. Well-organized body with clear headings
    4. Practical examples and real-world applications
    5. Actionable takeaways and tips
    6. Strong conclusion with key points
    
    Style guidelines:
    - Use clear, accessible language
    - Include relevant statistics and data
    - Add practical examples
    - Use bullet points and numbered lists for readability
    - Maintain an engaging, informative tone
    - Target length: 1500-2000 words""",
    expected_output="A well-written blog post with proper structure, engaging content, and practical insights.",
    agent=writer
)

editing_task = Task(
    description="""Review and edit the blog post for excellence.
    
    Check for:
    - Grammar, spelling, and punctuation errors
    - Clarity, flow, and coherence
    - Consistency in tone and style
    - Factual accuracy
    - Engagement and readability
    - Proper formatting and structure
    
    Make improvements while preserving the original voice and ensuring the content resonates with readers.""",
    expected_output="A polished, error-free blog post that flows smoothly and engages readers effectively.",
    agent=editor
)

seo_task = Task(
    description="""Optimize the blog post for SEO and discoverability.
    
    Focus on:
    - Optimize title for search intent
    - Ensure proper heading hierarchy (H1, H2, H3)
    - Include relevant keywords naturally
    - Optimize meta description
    - Check internal linking opportunities
    - Ensure mobile-friendly formatting
    - Optimize for featured snippets
    
    Provide the final optimized blog post with SEO recommendations.""",
    expected_output="An SEO-optimized blog post ready for publication with meta description and SEO notes.",
    agent=seo_specialist
)

crew = Crew(
    agents=[researcher, writer, editor, seo_specialist],
    tasks=[research_task, writing_task, editing_task, seo_task],
    process=Process.sequential,
    verbose=2,
    memory=True
)

def generate_blog(topic="AI Agents and Automation"):
    print(f"\n{'='*60}")
    print(f"🚀 Starting Blog Generation Process")
    print(f"📝 Topic: {topic}")
    print(f"{'='*60}\n")
    
    inputs = {
        "topic": topic
    }
    
    result = crew.kickoff(inputs=inputs)
    
    print(f"\n{'='*60}")
    print("✅ Blog Post Generated Successfully!")
    print(f"{'='*60}\n")
    
    return result

def save_blog_to_file(blog_content, filename="blog_post.md"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(str(blog_content))
    print(f"📄 Blog post saved to: {filename}")

if __name__ == "__main__":
    topic = input("Enter the blog topic (or press Enter for default): ").strip()
    if not topic:
        topic = "The Future of AI Agents in Software Development"
    
    blog_post = generate_blog(topic)
    save_blog_to_file(blog_post, f"blog_{topic.replace(' ', '_')[:30]}.md")
    print("\n" + str(blog_post))

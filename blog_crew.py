import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
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

researcher = Agent(
    role="Senior Research Analyst",
    goal="Discover cutting-edge developments in AI and technology",
    backstory="""You work at a leading tech think tank. 
    Your expertise lies in identifying emerging trends. 
    You have a knack for dissecting complex data and presenting actionable insights.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

writer = Agent(
    role="Tech Content Strategist",
    goal="Craft compelling blog posts about tech topics",
    backstory="""You are a renowned Content Strategist, known for your insightful and engaging articles. 
    You transform complex concepts into compelling narratives.""",
    verbose=True,
    allow_delegation=True,
    llm=llm
)

editor = Agent(
    role="Editor",
    goal="Ensure the blog post is polished and error-free",
    backstory="""You are a meticulous editor with an eye for detail. 
    You ensure every piece of content is grammatically correct and engaging.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

research_task = Task(
    description="""Research the latest developments in AI agents and automation.
    Focus on:
    - Recent breakthroughs in AI agent technology
    - Popular frameworks and tools
    - Real-world applications and use cases
    - Future trends and predictions
    
    Provide a comprehensive research summary with key points and insights.""",
    expected_output="A detailed research report covering the latest AI agent developments, frameworks, and trends.",
    agent=researcher
)

writing_task = Task(
    description="""Using the research findings, write an engaging blog post about AI agents.
    
    Requirements:
    - Catchy title
    - Engaging introduction
    - Well-structured body paragraphs
    - Clear explanations of complex concepts
    - Practical examples and use cases
    - Conclusion with key takeaways
    
    The tone should be informative yet accessible to a general tech audience.""",
    expected_output="A well-written blog post with a title, introduction, body, and conclusion about AI agents.",
    agent=writer
)

editing_task = Task(
    description="""Review and edit the blog post for:
    - Grammar and spelling errors
    - Clarity and flow
    - Engagement and readability
    - Factual accuracy
    
    Make necessary improvements while maintaining the original voice and style.""",
    expected_output="A polished, error-free blog post ready for publication.",
    agent=editor
)

crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, writing_task, editing_task],
    process=Process.sequential,
    verbose=2
)

def generate_blog(topic="AI Agents and Automation"):
    print(f"\n{'='*50}")
    print(f"Generating blog post about: {topic}")
    print(f"{'='*50}\n")
    
    result = crew.kickoff()
    
    print(f"\n{'='*50}")
    print("Blog Post Generated Successfully!")
    print(f"{'='*50}\n")
    
    return result

if __name__ == "__main__":
    blog_post = generate_blog()
    print(blog_post)

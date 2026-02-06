# AI Blog Writing Crew

A powerful AI-powered blog writing system using CrewAI framework that creates high-quality blog posts through a team of specialized AI agents.

## Features

- **Automated Research**: Research agent gathers comprehensive information using web search and scraping tools
- **Professional Writing**: Writer agent transforms research into engaging, well-structured content
- **Expert Editing**: Editor agent polishes content for grammar, flow, and readability
- **SEO Optimization**: SEO specialist optimizes content for search engines
- **Customizable Topics**: Generate blog posts on any tech topic
- **Markdown Output**: Save blog posts as Markdown files
- **ModelScope Integration**: Uses ModelScope's Qwen model for cost-effective AI generation

## Prerequisites

- Python 3.10 or higher (CrewAI requires Python 3.10+)
- ModelScope API key (free)
- (Optional) Serper API key for web search functionality
- uv package manager (recommended) or pip

## Installation

### Using uv (Recommended)

1. Install uv if you haven't already:
```bash
pip install uv
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
uv pip install -r requirements.txt
```

3. Activate the virtual environment:
```bash
# On Windows
.venv\Scripts\activate

# On Linux/Mac
source .venv/bin/activate
```

### Using pip (Alternative)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` file and add your API keys:
```
MODELSCOPE_API_KEY=ms-********************************
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
MODELSCOPE_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
SERPER_API_KEY=your_serper_api_key_here  # Optional
```

## Usage

### Basic Version

Run the basic version with predefined agents and tasks:

```bash
python blog_crew.py
```

### Advanced Version

Run the advanced version with web search and SEO optimization:

```bash
python advanced_blog_crew.py
```

You'll be prompted to enter a topic. Press Enter to use the default topic or type your own.

### Verify Setup

Check if your environment is properly configured:

```bash
python verify_setup.py
```

### 多智能体：寻找新闻并验证真假（News Discover & Verify）

整合 **d:\\news**（新闻发现）与 **d:\\orbitaai\\istrue**（真假验证）流程，一条命令完成：按兴趣从门户发现新闻 → 抓取全文 → 逐篇识别关键声明 → 生成核查计划 → 用 Serper 搜索验证 → 汇总报告。

**交互式运行：**

```bash
python news_discover_verify_crew.py
```

按提示输入：门户 URL、兴趣描述、最多验证篇数。

**命令行参数：**

```bash
python news_discover_verify_crew.py "https://news.yahoo.com/" "我对人工智能、科技比较感兴趣" 3
```

**环境变量：** 需在 `.env` 中配置 `MODELSCOPE_API_KEY`、`MODELSCOPE_BASE_URL`、`SERPER_API_KEY`（验证阶段搜索用）。

**输出：** 在 `reports/discover_verify_<时间戳>/` 下生成每篇的 `extracted_news.md`、`identified_claims.json`、`search_queries.json`、`verification_plan.md`、`verification_report.md`，以及汇总 `summary_report.md`。

## 项目代码结构

核心逻辑集中在 **`news_verify`** 包中，层次清晰、引用单一：

| 层级 | 目录/文件 | 说明 |
|------|-----------|------|
| 配置与工具 | `news_verify/llm.py` | LLM 配置（ModelScope/OpenAI 兼容） |
| | `news_verify/utils.py` | 通用工具：safe_slug、kickoff_with_retry |
| 工具 | `news_verify/tools/crawl.py` | 门户/文章爬虫 |
| | `news_verify/tools/verify.py` | 文件读取、Serper 搜索 |
| 智能体 | `news_verify/agents_news.py` | 兴趣抽取、选新闻、抓文章、事实核查、写报告 |
| | `news_verify/agents_verify.py` | 分析新闻、执行 Serper 验证 |
| 任务 | `news_verify/tasks_news.py` | 新闻侧任务定义 |
| | `news_verify/tasks_verify.py` | 验证侧任务工厂 |
| 流程 | `news_verify/pipeline_discover_verify.py` | 发现 → 逐篇验证 → 汇总 |
| | `news_verify/pipeline_fact_check.py` | 发现 → 逐篇事实核查 → 汇总 |
| 入口 | `news_discover_verify_crew.py` | 命令行入口（调用 news_verify） |
| | `news_fact_check_crew.py` | 命令行入口（调用 news_verify） |
| | `web_app/app.py` | Web UI，从 news_verify 导入 run_discover_and_verify |

根目录下的 `tools_verify.py` 功能已并入 `news_verify.tools.verify`，新代码请从 `news_verify` 包引用。

## How It Works

The system uses a team of AI agents working together:

1. **Researcher Agent**: Conducts comprehensive research using web search and scraping tools
2. **Writer Agent**: Transforms research findings into engaging blog content
3. **Editor Agent**: Polishes the content for grammar, flow, and readability
4. **SEO Specialist**: Optimizes the blog post for search engines

Each agent has specific roles, goals, and backstories that guide their work.

## ModelScope API Configuration

This project uses ModelScope's OpenAI-compatible API with the Qwen model:

```python
from openai import OpenAI

client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-*********************************',
)

response = client.chat.completions.create(
    model='Qwen/Qwen3-30B-A3B-Instruct-2507',
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你好'}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

## Customization

### Modify Agents

Edit `config/agents.yaml` to customize agent roles, goals, and backstories.

### Modify Tasks

Edit `config/tasks.yaml` to customize task descriptions and expected outputs.

### Add New Agents

You can add new specialized agents by:
1. Defining the agent in your Python script
2. Creating corresponding tasks
3. Adding the agent to the crew

## Output

Blog posts are saved as Markdown files with names like `blog_Your_Topic_Name.md`.

## Troubleshooting

### API Key Issues
- Ensure your `.env` file is in the same directory as the script
- Verify your ModelScope API key is valid
- Check that the API endpoint is accessible

### Import Errors
- Make sure all dependencies are installed: `uv pip install -r requirements.txt` or `pip install -r requirements.txt`
- Check Python version (3.8+ required)
- Ensure virtual environment is activated

### Rate Limiting
- ModelScope API may have rate limits
- Add delays between API calls if needed
- Consider using different models if available

### uv Issues
- Ensure uv is properly installed: `pip install uv`
- Check uv version: `uv --version`
- Try creating a new virtual environment: `uv venv`

## Cost Considerations

- ModelScope API is generally more cost-effective than OpenAI
- Advanced version with web search uses more API calls
- Monitor your API usage to control costs
- Consider using smaller models for testing

## License

This project is open source and available for educational and commercial use.

## Credits

Built with CrewAI framework and ModelScope's Qwen model.

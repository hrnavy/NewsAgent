"""LLM 配置：ModelScope/OpenAI 兼容，供所有 Agent 与流程使用。"""
import os

from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY")
MODELSCOPE_BASE_URL = os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
MODELSCOPE_MODEL = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")

if not MODELSCOPE_API_KEY:
    raise RuntimeError("MODELSCOPE_API_KEY is not set. Please add it to your .env file.")

llm = LLM(
    model=f"openai/{MODELSCOPE_MODEL}",
    api_key=MODELSCOPE_API_KEY,
    base_url=MODELSCOPE_BASE_URL,
    temperature=0.5,
)

# 单篇文章传给 LLM 的正文最大字符数，避免超出模型上下文
MAX_CONTENT_CHARS_FOR_LLM = 20000

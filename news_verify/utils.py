"""通用工具函数：文件名安全、Crew 重试、JSON 提取等。"""
import re
import time
from typing import Any

from crewai import Crew


def crew_output_string(result: Any) -> str:
    """从 Crew.kickoff 返回值得到纯文本，优先 raw/output 属性。"""
    if result is None:
        return ""
    for attr in ("raw", "output", "result"):
        raw = getattr(result, attr, None)
        if raw is not None and isinstance(raw, str):
            return raw.strip()
    return str(result).strip()


def extract_json_array(text: str, fix_unescaped_newlines: bool = True) -> str:
    """
    从可能含前后缀的文本中提取 JSON 数组 [...]，并可选地修复字符串值内的未转义换行。
    LLM 有时会在 title 等字段里输出真实换行，导致 json.loads 失败。
    """
    if not (text or "").strip():
        return "[]"
    match = re.search(r"\[.*\]", text, re.DOTALL)
    out = match.group(0) if match else text
    if fix_unescaped_newlines:
        # 将字符串内的真实换行替换为空格，避免 JSON 解析失败
        out = out.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return out


def safe_slug(text: str, max_len: int = 80) -> str:
    """生成 Windows 安全文件名 slug，去除非法字符。"""
    text = (text or "").strip()
    if not text:
        return "untitled"
    text = re.sub(r'[<>:"/\\|?*]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff _-]+", "", text).strip()
    text = text.replace(" ", "_")
    return (text[:max_len] if text else "untitled")


def kickoff_with_retry(crew: Crew, inputs: dict, max_retries: int = 2) -> Any:
    """对 Crew.kickoff 做 429 限流重试。"""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            return crew.kickoff(inputs=inputs)
        except Exception as e:
            last_err = e
            if "429" in str(e) or "RateLimit" in type(e).__name__:
                if attempt < max_retries:
                    time.sleep(30 * (attempt + 1))
                    continue
            raise
    raise last_err

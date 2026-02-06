# 验证阶段工具：文件读取、Serper 搜索（与 istrue 仓库一致）
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import json
import requests


class FileReadToolInput(BaseModel):
    file_path: str = Field(..., description="The absolute path to the file to read")


class FileReadTool(BaseTool):
    name: str = "File Reader"
    description: str = "Reads the content of a file from the specified file path"
    args_schema: Type[BaseModel] = FileReadToolInput

    def _run(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except FileNotFoundError:
            return f"Error: File not found at {file_path}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"


class SerperSearchToolInput(BaseModel):
    query: str = Field(..., description="The search query to execute")
    num_results: int = Field(default=10, description="Number of results to return (max 100)")


class SerperSearchTool(BaseTool):
    name: str = "Serper Search"
    description: str = "Searches the web using Serper API to verify claims and find information"
    args_schema: Type[BaseModel] = SerperSearchToolInput

    def _run(self, query: str, num_results: int = 10) -> str:
        try:
            api_key = os.getenv("SERPER_API_KEY")
            if not api_key:
                return "Error: SERPER_API_KEY environment variable is not set"

            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query, "num": min(num_results, 100)})
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

            response = requests.request("POST", url, headers=headers, data=payload)

            if response.status_code == 200:
                data = response.json()
                results = []
                if "organic" in data:
                    for item in data["organic"][:num_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                        })
                return json.dumps(results, ensure_ascii=False, indent=2)
            else:
                return f"Error: API request failed with status {response.status_code}: {response.text}"
        except Exception as e:
            return f"Error executing search: {str(e)}"

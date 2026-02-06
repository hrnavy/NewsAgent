# 快速开始指南

## 0. 检查Python版本

**重要**: CrewAI需要Python 3.10或更高版本。

```bash
# 检查Python版本
python --version
```

如果版本低于3.10，请先升级Python：
- Windows: 从 https://www.python.org/downloads/ 下载安装
- Linux/Mac: 使用pyenv或系统包管理器升级

## 1. 安装uv（如果还没有）

```bash
pip install uv
```

## 2. 创建虚拟环境并安装依赖

```bash
# 在项目目录下
uv venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
```

## 3. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑.env文件，确认以下配置：
MODELSCOPE_API_KEY=ms-dd2baa58-4a47-448b-93c6-1a14869a170e
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
MODELSCOPE_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
```

## 4. 验证环境

```bash
python verify_setup.py
```

## 5. 运行项目

### 基础版本
```bash
python blog_crew.py
```

### 高级版本（推荐）
```bash
python advanced_blog_crew.py
```

## 6. 查看生成的博客

博客文章会保存为Markdown文件，文件名格式：`blog_Your_Topic_Name.md`

## 常见问题

### Q: Python版本不兼容怎么办？
A: CrewAI需要Python 3.10或更高版本。如果当前版本是3.8或3.9，请升级到3.10+。

### Q: uv安装失败怎么办？
A: 可以使用pip作为替代方案：`pip install -r requirements.txt`

### Q: 如何更换ModelScope模型？
A: 修改.env文件中的MODELSCOPE_MODEL参数

### Q: API调用失败怎么办？
A: 检查网络连接，确认API密钥有效，检查API端点是否可访问

### Q: 如何降低成本？
A: ModelScope API已经比OpenAI便宜很多，还可以考虑使用更小的模型

## 下一步

- 查看README.md了解详细功能
- 修改config/agents.yaml自定义代理
- 修改config/tasks.yaml自定义任务
- 阅读IMPLEMENTATION_LOG.md了解实现细节

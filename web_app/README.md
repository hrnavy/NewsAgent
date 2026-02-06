# 新闻发现与验证 · 本地展示页

仅限本机使用：展示 Agent 执行过程，简约界面 + 动画，所有输出记录到 `runs/run_*.log`。

- **不对外**：服务只监听 `127.0.0.1:5050`，仅供本机访问。
- **API 费用**：流程会调用 ModelScope / Serper，请勿让他人运行。

## 运行

在项目根目录（`d:\vibing crawl`）下：

```bash
# 安装依赖（若尚未安装 Flask）
pip install flask

# 启动本地服务
python web_app/app.py
```

浏览器打开：**http://127.0.0.1:5050**

填写门户 URL、兴趣描述、篇数后点击「开始运行」，页面会实时展示各步骤；日志保存在项目根目录下的 `runs/run_YYYYMMDD_HHMMSS.log`。

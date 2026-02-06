"""
本地网页：展示 Agent 执行过程，仅限本机使用。
- 简约界面、动画展示步骤
- 记录所有输出到 runs/run_*.log
- 不对外暴露，API 仅本机调用
"""
import os
import sys
import json
import queue
import threading
import datetime as dt
from pathlib import Path
from flask import Flask, request, Response, send_from_directory

# 项目根目录加入 path，便于从任意工作目录运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from news_verify import run_discover_and_verify

app = Flask(__name__, static_folder="static")
# 当前运行产生的事件队列（单例，一次只跑一个任务）
event_queue = queue.Queue()
# 当前运行日志文件路径
current_log_path = None
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)


def _get_llm_info():
    """从环境读取当前 LLM 配置，供前端展示。"""
    model = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")
    base = os.getenv("MODELSCOPE_BASE_URL", "")
    if "modelscope" in (base or "").lower():
        provider = "ModelScope"
    elif os.getenv("OPENAI_API_KEY") and not os.getenv("MODELSCOPE_API_KEY"):
        provider = "OpenAI"
    else:
        provider = "ModelScope"
    return {"llm_provider": provider, "llm_model": model}


def run_pipeline(portal_url: str, user_interest_desc: str, max_articles: int):
    global current_log_path
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    current_log_path = RUNS_DIR / f"run_{ts}.log"
    log_file = open(current_log_path, "w", encoding="utf-8")

    # 先推送本次任务参数（含 LLM 信息），便于终端展示
    try:
        llm_info = _get_llm_info()
        event_queue.put_nowait({
            "step_id": "run_params",
            "status": "info",
            "message": "任务参数",
            "detail": {
                "portal_url": portal_url,
                "user_interest_desc": user_interest_desc[:200],
                "max_articles": max_articles,
                "llm_provider": llm_info["llm_provider"],
                "llm_model": llm_info["llm_model"],
            },
        })
    except Exception:
        pass

    def on_event(step_id: str, status: str, message: str, detail: any):
        line = f"[{dt.datetime.now().isoformat()}] {step_id} | {status} | {message}"
        if detail is not None:
            try:
                line += " | " + (json.dumps(detail, ensure_ascii=False) if not isinstance(detail, str) else detail)
            except Exception:
                line += " | (detail)"
        log_file.write(line + "\n")
        log_file.flush()
        try:
            # 传完整 detail 供前端展示（含 tool_output、files）；保持可序列化
            if detail is not None and not isinstance(detail, (str, type(None))):
                try:
                    json.dumps(detail)
                except (TypeError, ValueError):
                    detail = str(detail)[:500]
            event_queue.put_nowait({"step_id": step_id, "status": status, "message": message, "detail": detail})
        except Exception:
            pass

    try:
        result = run_discover_and_verify(
            portal_url,
            user_interest_desc,
            max_articles=max_articles,
            on_event=on_event,
        )
        event_queue.put_nowait({"step_id": "complete", "status": "done", "message": "流程结束", "detail": result[:500] if result else None})
    except Exception as e:
        log_file.write(f"[{dt.datetime.now().isoformat()}] error | {e}\n")
        log_file.flush()
        event_queue.put_nowait({"step_id": "error", "status": "error", "message": str(e), "detail": None})
    finally:
        log_file.close()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/config")
def api_config():
    """返回当前 LLM 等配置，供前端展示「当前模型」。"""
    return json.dumps(_get_llm_info(), ensure_ascii=False)


@app.route("/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}
    portal_url = (data.get("portal_url") or "").strip() or "https://apnews.com/"
    user_interest_desc = (data.get("user_interest_desc") or "").strip() or "我对特朗普对外政策比较感兴趣"
    max_articles = int(data.get("max_articles") or 1)
    max_articles = max(1, min(10, max_articles))

    # 清空旧事件
    while True:
        try:
            event_queue.get_nowait()
        except queue.Empty:
            break

    thread = threading.Thread(
        target=run_pipeline,
        args=(portal_url, user_interest_desc, max_articles),
        daemon=True,
    )
    thread.start()
    return json.dumps({"ok": True, "message": "已开始运行"})


def event_stream():
    while True:
        try:
            event = event_queue.get(timeout=30)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("step_id") in ("complete", "error"):
                break
        except queue.Empty:
            yield f"data: {json.dumps({'step_id': 'ping', 'status': 'ping', 'message': '', 'detail': None})}\n\n"


@app.route("/events")
def events():
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/file")
def serve_file():
    """安全地提供 reports/ 或 runs/ 下的文件，path 为相对路径（可用 / 或 \\）。"""
    raw = (request.args.get("path") or "").strip()
    if not raw:
        return {"error": "missing path"}, 400
    path = Path(raw.replace("\\", "/").lstrip("/"))
    if ".." in path.parts or path.is_absolute():
        return {"error": "invalid path"}, 400
    full = (ROOT / path).resolve()
    reports = (ROOT / "reports").resolve()
    runs = (ROOT / "runs").resolve()
    if not (str(full).startswith(str(reports)) or str(full).startswith(str(runs))):
        return {"error": "path not allowed"}, 403
    if not full.is_file():
        return {"error": "not found"}, 404
    return send_from_directory(full.parent, full.name, as_attachment=False)


if __name__ == "__main__":
    
    # 仅监听本机。默认 port=0 由系统分配可用端口，避免本机 5050/5051 等被保留导致“访问套接字权限不允许”
    env_port = os.environ.get("PORT", os.environ.get("FLASK_PORT", ""))
    port = int(env_port) if env_port.isdigit() else 0
    if port == 0:
        print("Using system-assigned port (see 'Running on http://...' below).")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

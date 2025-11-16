from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from langserve import add_routes
from typing import Any
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("void-system")

app = FastAPI(title="Void System Core + LangServe")

# 配置CORS（关键：允许前端跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修复会话中间件
@app.middleware("http")
async def persona_session_middleware(request: Request, call_next):
    # 仅处理POST请求且路径为persona的invoke
    if request.url.path == "/lc/persona/invoke" and request.method == "POST":
        try:
            # 读取原始请求体
            body_bytes = await request.body()
            if not body_bytes:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "请求体不能为空"}
                )

            # 解析JSON
            body = json.loads(body_bytes)
            
            # 确保configurable包含session_id
            if "configurable" not in body:
                body["configurable"] = {}
            if "session_id" not in body["configurable"]:
                session_id = f"persona-{uuid.uuid4().hex}"
                body["configurable"]["session_id"] = session_id
                logger.info(f"生成默认session_id: {session_id}")
            else:
                logger.info(f"使用现有session_id: {body['configurable']['session_id']}")

            # 重新序列化并更新请求体（关键修复：转为字节流）
            modified_body = json.dumps(body).encode("utf-8")
            request._body = modified_body  # 更新原始请求体

            # 清除FastAPI的JSON解析缓存
            if hasattr(request, "_json"):
                del request._json

            # 更新Content-Length头
            request.headers.__dict__["_list"].append(
                (b"content-length", str(len(modified_body)).encode())
            )

        except json.JSONDecodeError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "无效的JSON格式"}
            )

    # 处理其他请求
    response = await call_next(request)
    return response


# 临时调试中间件：打印 /lc/qa 的 POST 原始请求体（仅调试用，生产环境请移除）
@app.middleware("http")
async def debug_qa_request_body_middleware(request: Request, call_next):
    # 只针对 qa invoke POST 打印
    try:
        if request.method == "POST" and request.url.path.startswith("/lc/qa"):
            body_bytes = await request.body()
            # 有时 uvicorn/console 会缓冲输出，使用 logger 也可以
            print("[DEBUG] RAW QA BODY:", body_bytes)

            # 恢复 body 以便后续处理
            request._body = body_bytes
            if hasattr(request, "_json"):
                del request._json

            # 更新 Content-Length 头（避免与原始长度不符）
            try:
                headers_list = request.headers.__dict__["_list"]
                # 移除已有的 content-length
                headers_list[:] = [h for h in headers_list if h[0].lower() != b"content-length"]
                headers_list.append((b"content-length", str(len(body_bytes)).encode()))
            except Exception:
                pass
    except Exception as e:
        print("[DEBUG] failed to read body:", e)

    return await call_next(request)

# 注册无需会话的链
# 强制 QA runnable 接受任意类型的 `input`，避免 Pydantic 在入口层拒绝 dict/string
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")


# 最后注册persona链
add_routes(app, load_persona_chain(), path="/lc/persona")

@app.post("/")
def read_root():
    return {"system": "VOID CORE ACTIVE", "status": "running"}

@app.get("/routes")
def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({"path": route.path, "methods": list(route.methods)})
    return routes


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"❌ 未捕获异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "系统内部错误", "detail": str(exc)}
    )


@app.lifespan("startup")
async def on_startup():
    # 使用 logger 在 Uvicorn 的 worker 进程启动时打印，兼容 --reload 和外部 uvicorn 调用
    logger.info("🚀 Void System Backend 已启动，监听端口 8000")

if __name__ == "__main__":
    uvicorn.run('main:app', host="127.0.0.1", port=8000, log_level="info", reload=True)
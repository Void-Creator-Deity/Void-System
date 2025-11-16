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

# 注册链
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")
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

if __name__ == "__main__":
    uvicorn.run('main:app', host="127.0.0.1", port=8000, log_level="info", reload=True)
    print("🚀 Void System Backend 已启动，监听端口 8000")
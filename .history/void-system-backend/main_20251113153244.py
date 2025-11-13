from fastapi import FastAPI, Request
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware  # 导入CORS中间件

app = FastAPI(title="Void System Core + LangServe")

# ✅ 重新添加并配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端地址（精确匹配）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法（包括OPTIONS）
    allow_headers=["*"],  # 允许所有请求头
)

# 自动注册 LangServe routes
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# persona 路由逻辑（保持不变）
@app.middleware("http")
async def default_session_middleware(request: Request, call_next):
    if request.url.path.endswith("/invoke"):
        try:
            body = await request.json()
            if "configurable" not in body:
                body["configurable"] = {"session_id": "default"}
            elif "session_id" not in body["configurable"]:
                body["configurable"]["session_id"] = "default"
            request._body = body
        except Exception:
            pass
    response = await call_next(request)
    return response

add_routes(app, load_persona_chain(), path="/lc/persona")from fastapi import FastAPI, Request
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware  # 导入CORS中间件

app = FastAPI(title="Void System Core + LangServe")

# ✅ 重新添加并配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端地址（精确匹配）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法（包括OPTIONS）
    allow_headers=["*"],  # 允许所有请求头
)

# 自动注册 LangServe routes
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# persona 路由逻辑（保持不变）
@app.middleware("http")
async def default_session_middleware(request: Request, call_next):
    if request.url.path.endswith("/invoke"):
        try:
            body = await request.json()
            if "configurable" not in body:
                body["configurable"] = {"session_id": "default"}
            elif "session_id" not in body["configurable"]:
                body["configurable"]["session_id"] = "default"
            request._body = body
        except Exception:
            pass
    response = await call_next(request)
    return response

add_routes(app, load_persona_chain(), path="/lc/persona")
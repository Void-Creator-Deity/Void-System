from fastapi import FastAPI, Request
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain

app = FastAPI(title="Void System Core + LangServe")

# 自动注册 LangServe routes
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# ✅ 修改 persona 路由逻辑，给默认 session_id
@app.middleware("http")
async def default_session_middleware(request: Request, call_next):
    if request.url.path.endswith("/invoke"):
        try:
            body = await request.json()
            if "configurable" not in body:
                body["configurable"] = {"session_id": "default"}
            elif "session_id" not in body["configurable"]:
                body["configurable"]["session_id"] = "default"
            request._body = body  # 直接修改请求体
        except Exception:
            pass
    response = await call_next(request)
    return response

add_routes(app, load_persona_chain(), path="/lc/persona")

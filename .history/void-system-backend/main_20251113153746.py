from fastapi import FastAPI, Request
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware  # 恢复CORS中间件
import json  # 用于JSON序列化

app = FastAPI(title="Void System Core + LangServe")

# 1. 先添加CORS中间件（解决跨域问题，必须在路由注册前添加）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 注册不需要会话的链（先注册非persona链）
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# 3. 为persona链添加会话中间件（精确匹配persona的invoke路径）
@app.middleware("http")
async def persona_session_middleware(request: Request, call_next):
    # 只处理persona的invoke请求
    if request.url.path == "/lc/persona/invoke" and request.method == "POST":
        try:
            # 读取原始请求体
            body_bytes = await request.body()
            body = json.loads(body_bytes) if body_bytes else {}
            
            # 强制添加session_id（如果不存在）
            if "configurable" not in body:
                body["configurable"] = {}
            body["configurable"]["session_id"] = body["configurable"].get("session_id", "default")
            
            # 将修改后的body转换为字节，重新赋值给请求体
            request._body = json.dumps(body).encode()
        except Exception as e:
            print(f"处理persona请求体错误: {e}")
    
    response = await call_next(request)
    return response

# 4. 最后注册persona链
add_routes(app, load_persona_chain(), path="/lc/persona")

@app.get("/")
def read_root():
    return {"system": "VOID CORE ACTIVE"}
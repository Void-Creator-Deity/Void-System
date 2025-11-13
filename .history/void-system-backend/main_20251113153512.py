from fastapi import FastAPI, Request
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware  # 重新添加CORS中间件
import json  # 导入json模块用于序列化

app = FastAPI(title="Void System Core + LangServe")

# 先添加CORS中间件（解决跨域问题）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自动注册 LangServe routes
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# 修改 persona 路由逻辑，正确处理请求体
@app.middleware("http")
async def default_session_middleware(request: Request, call_next):
    if request.url.path.endswith("/invoke"):
        try:
            # 1. 读取原始请求体（字节）并解析为字典
            body_bytes = await request.body()
            body = json.loads(body_bytes) if body_bytes else {}  # 处理空请求体
            
            # 2. 补充默认session_id
            if "configurable" not in body:
                body["configurable"] = {"session_id": "default"}
            elif "session_id" not in body["configurable"]:
                body["configurable"]["session_id"] = "default"
            
            # 3. 关键修复：将字典转换为JSON字符串的字节形式，再赋值给_body
            request._body = json.dumps(body).encode()  # 转为字节类型
        except Exception as e:
            print(f"处理请求体出错: {e}")  # 打印错误便于调试
    response = await call_next(request)
    return response

add_routes(app, load_persona_chain(), path="/lc/persona")
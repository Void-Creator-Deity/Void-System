from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid  # 用于生成唯一session_id
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("void-system")

app = FastAPI(title="Void System Core + LangServe")

# 1. CORS中间件（放在最前面）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 精确指定前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 注册无需会话的链
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")

# 3. 增强版会话中间件
@app.middleware("http")
async def persona_session_middleware(request: Request, call_next):
    # 只处理persona的invoke请求
    if request.url.path == "/lc/persona/invoke" and request.method == "POST":
        try:
            # 读取并解析请求体
            body_bytes = await request.body()
            if not body_bytes:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "请求体不能为空"}
                )

            body = json.loads(body_bytes)
            
            # 初始化配置字典
            if "configurable" not in body:
                body["configurable"] = {}
            
            # 生成唯一session_id（如果不存在）
            if "session_id" not in body["configurable"]:
                default_session = f"default-{uuid.uuid4().hex[:8]}"
                body["configurable"]["session_id"] = default_session
                logger.info(f"生成默认session_id: {default_session}")
            else:
                logger.info(f"使用现有session_id: {body['configurable']['session_id']}")

            # 重新序列化请求体（确保编码正确）
            request._body = json.dumps(body, ensure_ascii=False).encode("utf-8")

        except json.JSONDecodeError:
            logger.error("请求体不是有效的JSON格式")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "无效的JSON格式"}
            )
        except Exception as e:
            logger.error(f"处理会话中间件时出错: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "服务器处理请求时出错"}
            )

    # 处理请求
    response = await call_next(request)
    return response

# 4. 注册persona链
add_routes(app, load_persona_chain(), path="/lc/persona")

@app.get("/")
def read_root():
    return {"system": "VOID CORE ACTIVE", "status": "running"}
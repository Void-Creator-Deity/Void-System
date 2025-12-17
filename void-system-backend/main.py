"""
Void System Backend - Main Application
虚空系统后端主应用，基于FastAPI构建

项目架构说明：
- 使用FastAPI构建高性能异步API
- 模块化设计：config.py(配置), errors.py(错误处理), utils.py(工具函数)
- 清晰的代码组织：api/目录包含业务逻辑，lc_server/包含AI服务
- 统一的响应格式和错误处理
- 支持DeepSeek风格的文件上传和RAG问答

TODO:
- [ ] 完善单元测试覆盖率
- [ ] 添加Redis缓存支持
- [ ] 实现用户文档版本控制
- [ ] 优化向量搜索性能
- [ ] 添加API速率限制
- [ ] 实现微服务架构迁移计划
"""
import os
import time
import uuid
import secrets
from contextlib import asynccontextmanager
from typing import Any, Optional, List, Dict, Literal, Union, AsyncGenerator, Callable, Awaitable
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException, UploadFile, File, Form, Query, Body, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ConfigDict, field_validator
from langserve import add_routes
import bcrypt
from jose import JWTError, jwt
import uvicorn
import logging
from dotenv import load_dotenv

# 导入项目模块 - 实现更好的解耦
from config import config
from errors import ErrorCode, VoidSystemException, create_auth_error, create_file_error
from tools.utils import (
    get_file_extension, is_allowed_file, validate_file_size,
    generate_unique_filename, ensure_directory_exists, get_current_timestamp,
    paginate_results, sanitize_string, time_function_execution
)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger: logging.Logger = logging.getLogger("void-system")

# 导入数据库模块
from database import Database

# ==================== 配置验证 ====================
# 导入配置模块
from config import Config

# 验证配置
if Config.SECRET_KEY == Config._default_secret:
    logger.warning("⚠️ 使用随机生成的SECRET_KEY，生产环境请设置环境变量 SECRET_KEY")
    logger.warning("⚠️ 当前SECRET_KEY(仅用于开发): " + Config.SECRET_KEY[:16] + "...")
    logger.info("💡 设置方法: export SECRET_KEY='your-secure-random-key-here'")
    logger.info("💡 生成安全密钥: python tools/generate_secret.py --export")
elif len(Config.SECRET_KEY) < 32:
    logger.warning("⚠️ SECRET_KEY长度不足32字符，建议使用更长的密钥以提高安全性")
else:
    logger.info("✅ SECRET_KEY配置正确")

# ==================== 数据库实例 ====================
db_instance: Optional[Database] = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    global db_instance
    # 启动时
    logger.info("🚀 Void System Backend 正在启动...")
    try:
        db_instance = Database("void_system.db")
        logger.info("✅ 数据库连接已建立")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise
    
    yield
    
    # 关闭时
    logger.info("🛑 Void System Backend 正在关闭...")
    if db_instance:
        try:
            db_instance.close()
            logger.info("✅ 数据库连接已关闭")
        except Exception as e:
            logger.error(f"❌ 数据库关闭失败: {e}")

# ==================== Pydantic 模型定义 ====================
class APIResponse(BaseModel):
    """标准API响应模型"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {"key": "value"},
                "error_code": None,
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

class UserRegister(BaseModel):
    """用户注册模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    nickname: Optional[str] = Field(None, max_length=30)
    
    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v: Optional[str]) -> Optional[str]:
        # 如果昵称为空字符串，则返回None
        if v is not None and v.strip() == "":
            return None
        # 如果昵称不为None，则验证最小长度
        if v is not None and len(v) < 2:
            raise ValueError('昵称长度至少为2个字符')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        # 如果邮箱为空字符串，则返回None
        if v is not None and v.strip() == "":
            return None
        # 如果邮箱不为None，则验证其格式
        if v is not None:
            # 更严格的邮箱格式验证
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('无效的邮箱地址')
        return v
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        # 简单的密码强度检查
        if v.isalpha() or v.isnumeric():
            raise ValueError('密码应包含字母和数字')
        return v

class TaskCreate(BaseModel):
    """任务创建模型"""
    task_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field("", max_length=500)
    related_attrs: Optional[Dict[str, Any]] = None
    estimated_time: Optional[int] = Field(30, ge=1, le=480)  # 1-480分钟
    reward_coins: Optional[int] = Field(10, ge=0, le=1000)
    category_id: Optional[str] = None
    
    @field_validator('related_attrs')
    @classmethod
    def validate_related_attrs(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            for key, value in v.items():
                if not isinstance(value, (int, float)):
                    raise ValueError(f"属性 {key} 的值必须是数字")
        return v

class TaskUpdate(BaseModel):
    """任务更新模型"""
    status: Optional[Literal['pending', 'in_progress', 'completed', 'failed']] = None
    proof_data: Optional[Dict[str, Any]] = None
    self_evaluation: Optional[Dict[str, Any]] = None

class AttributeCreate(BaseModel):
    """属性创建模型"""
    attr_name: str = Field(..., min_length=1, max_length=50)
    max_value: int = Field(default=100, ge=1, le=999)
    description: Optional[str] = Field("", max_length=200)
    icon: Optional[str] = "📊"

class AttributeUpdate(BaseModel):
    """属性更新模型"""
    attr_value: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    max_value: Optional[int] = Field(None, ge=1, le=999)

class TaskCategoryCreate(BaseModel):
    """任务类别创建模型"""
    category_name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field("", max_length=200)
    icon: Optional[str] = "📚"
    color: Optional[str] = "#3B82F6"  # 蓝色

class TaskCategoryUpdate(BaseModel):
    """任务类别更新模型"""
    category_name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class ShopItem(BaseModel):
    """商店商品模型"""
    item_id: str
    item_name: str
    price: int
    category: str
    description: str
    effect: Optional[Dict[str, Any]] = None

class PurchaseRequest(BaseModel):
    """购买请求模型"""
    quantity: int = Field(1, ge=1, le=10)

# ==================== 自定义异常 ====================
class VoidSystemException(Exception):
    """虚空系统自定义异常"""
    def __init__(self, message: str, error_code: Optional[str] = None, status_code: int = 400) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

# ==================== 统一响应工具 ====================
def create_success_response(
    message: str,
    data: Optional[Any] = None,
    request_id: Optional[str] = None
) -> APIResponse:
    """
    创建成功的API响应

    Args:
        message: 响应消息
        data: 响应数据
        request_id: 请求ID（可选）

    Returns:
        APIResponse对象
    """
    return APIResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id
    )

def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    data: Optional[Any] = None,
    request_id: Optional[str] = None
) -> APIResponse:
    """
    创建失败的API响应

    Args:
        message: 错误消息
        error_code: 错误码
        data: 额外数据（可选）
        request_id: 请求ID（可选）

    Returns:
        APIResponse对象
    """
    return APIResponse(
        success=False,
        message=message,
        error_code=error_code,
        data=data,
        request_id=request_id
    )

# ==================== 依赖注入 ====================
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="api/v1/token")

def get_db() -> Database:
    """获取数据库实例依赖"""
    if db_instance is None:
        raise VoidSystemException.from_error_code(
            ErrorCode.SYSTEM_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return db_instance

def get_user_service(db: Database = Depends(get_db)):
    """获取用户服务实例"""
    from services.user_service import UserService
    return UserService(db)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前认证用户
    Args:
        token: JWT 令牌
        db: 数据库实例
    Returns:
        用户信息字典
    Raises:
        VoidSystemException: 如果令牌无效或用户不存在
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise VoidSystemException(
                message="认证凭据无效",
                error_code="INVALID_CREDENTIALS",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
    except JWTError:
        raise VoidSystemException(
            message="认证凭据无效",
            error_code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    user: Optional[Dict[str, Any]] = db.get_user_by_username(username)
    if user is None:
        raise VoidSystemException(
            message="用户不存在",
            error_code="USER_NOT_FOUND",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return user

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前认证的管理员用户
    Args:
        current_user: 当前认证用户
    Returns:
        管理员用户信息字典
    Raises:
        VoidSystemException: 如果用户不是管理员
    """
    if current_user.get("role", "user") != "admin":
        raise VoidSystemException(
            message="需要管理员权限",
            error_code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    return current_user

# ==================== JWT 认证相关函数 ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    Returns:
        密码是否匹配
    """
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    Args:
        password: 明文密码
    Returns:
        哈希后的密码
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    Returns:
        JWT 令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access_token"
    })
    
    encoded_jwt: str = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建刷新令牌
    Args:
        data: 要编码的数据
    Returns:
        JWT 刷新令牌
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh_token"
    })
    
    encoded_jwt: str = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )
    return encoded_jwt

# ==================== FastAPI 应用初始化 ====================
app = FastAPI(
    title="Void System Core API",
    description="虚空系统后端 API，集成 LangChain 服务",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

# ==================== 中间件 ====================
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """请求日志中间件"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(f"Request {request_id}: {request.method} {request.url}")
    
    # 记录请求体（限制大小，避免敏感信息）
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body and len(body) < 5000:  # 限制日志大小
                try:
                    body_str = body.decode('utf-8')
                    if "password" not in body_str.lower():  # 避免记录密码
                        logger.debug(f"Request {request_id} body: {body_str}")
                except:
                    pass
    except Exception as e:
        logger.debug(f"无法读取请求体: {e}")
    
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request {request_id} 处理失败: {e}", exc_info=True)
        raise
    
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.2f}ms")
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response

# ==================== 异常处理器 ====================
@app.exception_handler(VoidSystemException)
async def void_system_exception_handler(request: Request, exc: VoidSystemException) -> JSONResponse:
    """自定义异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=exc.message,
            error_code=exc.error_code,
            request_id=getattr(request.state, 'request_id', None)
        ).model_dump()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    logger.error(f"请求验证错误: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            success=False,
            message="请求数据验证失败",
            error_code="VALIDATION_ERROR",
            data={"errors": [str(error) for error in exc.errors()]},
            request_id=getattr(request.state, 'request_id', None)
        ).model_dump()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=getattr(request.state, 'request_id', None)
        ).model_dump(),
        headers=exc.headers
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    logger.error(f"未捕获异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(
            success=False,
            message="系统内部错误",
            error_code="INTERNAL_SERVER_ERROR",
            request_id=getattr(request.state, 'request_id', None)
        ).model_dump()
    )

# 辅助函数：净化AI响应
def purify_ai_response(raw_content: Any) -> str:
    """
    移除LangChain/模型响应中的思考过程(如<think>标签)和内部指令，
    只返回给用户看的最终答案。
    """
    import re
    
    # 1. 确保输入是字符串类型
    if not isinstance(raw_content, str):
        # 如果是对象，尝试获取content属性，否则转换为字符串
        if hasattr(raw_content, 'content'):
            raw_content = raw_content.content
        else:
            raw_content = str(raw_content)
    
    # 2. 移除整个<think>...</think>块及其内容
    purified = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
    
    # 3. 移除可能残留的“AI引导精灵”等内部角色提示
    purified = re.sub(r'^你是.*?精灵[。\n]*', '', purified)
    
    # 4. 清理多余的空行和首尾空白
    purified = purified.strip()
    
    # 5. 如果净化后的内容为空，返回一个默认响应
    if not purified:
        purified = "我理解了你的请求，让我为你提供帮助。"
    
    return purified

# 流式响应支持
from sse_starlette.sse import EventSourceResponse
import json
from typing import Dict, Any

# 流式响应端点（支持旧路径重定向）
@app.post("/stream-chat")
async def stream_chat_legacy(user_input: Dict[str, Any]):
    """
    旧流式响应路径重定向
    """
    # 直接调用新端点的处理函数
    return await stream_chat_endpoint(user_input)

@app.post("/api/stream-chat")
async def stream_chat_endpoint(user_input: Dict[str, Any]):
    """
    流式响应接口，提供打字机效果
    """
    import asyncio
    from io import StringIO
    
    try:
        user_topic = user_input.get("topic", "")
        user_text = user_input.get("text", "")
        user_question = user_input.get("question", "")
        chain_type = user_input.get("type", "persona")
        
        # 根据类型选择不同的链
        if chain_type == "advisor":
            from services.ai_services.advisor_chain import load_task_chain
            chain = load_task_chain()
            input_data = {"topic": user_topic}
        elif chain_type == "qa":
            from services.ai_services.qa_chain import load_qa_chain
            chain = load_qa_chain()
            input_data = {"question": user_question}
        else:  # 默认persona
            from services.ai_services.persona_chain import load_persona_chain
            chain = load_persona_chain()
            # 从输入中提取或生成session_id
            session_id = user_input.get("session_id", "user-" + str(asyncio.get_event_loop().time()).replace(".", "")[:10])
            input_data = {
                "text": user_text,
                "config": {
                    "configurable": {
                        "session_id": session_id
                    }
                }
            }
        
        async def event_generator():
            buffer = StringIO()
            inside_think_block = False
            
            # 尝试流式调用链
            try:
                # 注意：RunnableLambda对象可能不直接支持astream方法，先尝试invoke
                # 然后模拟流式输出，提供打字机效果
                result = chain.invoke(input_data)
                
                # 确保result是字符串类型
                if hasattr(result, 'content'):
                    result_text = result.content
                elif isinstance(result, dict) and 'content' in result:
                    result_text = result['content']
                else:
                    result_text = str(result)
                
                # 净化内容
                purified_result = purify_ai_response(result_text)
                
                # 模拟打字机效果，逐个字符发送
                if purified_result:
                    for char in purified_result:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "content": char,
                                "finished": False
                            })
                        }
                        # 模拟打字机效果的延迟
                        await asyncio.sleep(0.05)
            except Exception as e:
                # 处理任何异常，返回错误信息
                logger.error(f"流式响应处理失败: {e}")
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "content": f"抱歉，处理请求时出现错误: {str(e)}",
                        "finished": True
                    })
                }
                return
            
            # 发送结束信号
            yield {
                "event": "message",
                "data": json.dumps({
                    "content": "",
                    "finished": True
                })
            }
        
        return EventSourceResponse(event_generator())
    except Exception as e:
        logger.error(f"❌ 流式响应失败: {e}")
        # 返回错误信息
        return {
            "success": False,
            "error": str(e)
        }

# ==================== LangChain 服务路由 ====================
try:
    from services.ai_services.qa_chain import load_qa_chain
    from services.ai_services.advisor_chain import load_task_chain
    from services.ai_services.persona_chain import load_persona_chain
    
    # 净化AI响应，移除思考过程
    def get_purified_chain(chain):
        from langchain_core.runnables import RunnableLambda
        from langchain_core.output_parsers import StrOutputParser
        
        def purify_output(output):
            """净化AI输出，移除思考过程"""
            import re
            
            # 处理不同类型的输出
            if isinstance(output, dict):
                # 如果是字典，检查是否有content字段
                if 'content' in output:
                    output['content'] = purify_ai_response(output['content'])
                return output
            elif hasattr(output, 'content'):
                # 如果是有content属性的对象
                output.content = purify_ai_response(output.content)
                return output
            else:
                # 直接净化字符串输出
                return purify_ai_response(str(output))
        
        # 创建净化链
        return chain | RunnableLambda(purify_output)
    
    add_routes(app, get_purified_chain(load_qa_chain()), path="/api/lc/qa")
    add_routes(app, get_purified_chain(load_task_chain()), path="/api/lc/advisor")
    add_routes(app, get_purified_chain(load_persona_chain()), path="/api/lc/persona")
    logger.info("✅ LangChain 服务路由已注册")
    
    # 添加一个简单的测试端点，用于验证后端是否能正确返回结构化数据
    @app.post("/api/test-advisor")
    async def test_advisor_endpoint(request: Request):
        """测试端点：直接返回结构化任务建议"""
        from services.ai_services.advisor_chain import safe_invoke_chain, load_task_chain
        
        # 从请求体中获取topic
        request_data = await request.json()
        topic = request_data.get("topic", "")
        
        chain = load_task_chain()
        result = safe_invoke_chain(chain, topic)
        
        return create_success_response("任务建议生成成功", data=result)
        
except ImportError as e:
    logger.warning(f"⚠️ LangChain 服务未找到: {e}")
except Exception as e:
    logger.error(f"❌ LangChain 服务注册失败: {e}")

# ==================== 系统信息路由 ====================
@app.get("/", summary="系统状态", tags=["系统"], response_model=APIResponse)
async def read_root() -> APIResponse:
    """系统根路径，返回系统状态"""
    return create_success_response("系统运行正常", data={
        "system": "VOID CORE ACTIVE",
        "status": "running",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.get("/api/health", summary="健康检查", tags=["系统"], response_model=APIResponse)
async def health_check(db: Database = Depends(get_db)) -> APIResponse:
    """系统健康检查端点"""
    try:
        # 测试数据库连接
        db_status = "healthy"
        db.test_connection()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"数据库健康检查失败: {e}")
    
    return APIResponse(
        success=True,
        message="系统健康状态",
        data={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_status,
            "version": "0.2.0"
        }
    )

@app.get("/api/routes", summary="获取所有API路由", tags=["系统"], response_model=APIResponse)
async def list_routes() -> APIResponse:
    """列出所有可用的 API 路由"""
    routes: List[Dict[str, Any]] = []
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", ["GET"])
            routes.append({
                "path": route.path,
                "methods": list(methods),
                "name": getattr(route, "name", ""),
                "summary": getattr(route, "summary", "")
            })
    
    return create_success_response("可用路由列表", data={"routes": routes})

# ==================== 用户认证相关路由 ====================
@app.post("/api/token", summary="用户登录", tags=["认证"], response_model=APIResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service = Depends(get_user_service)
) -> APIResponse:
    """
    用户登录，获取访问令牌

    - **username**: 用户名
    - **password**: 密码
    """
    auth_result = user_service.authenticate_user(form_data.username, form_data.password)
    return create_success_response("登录成功", data=auth_result)

@app.post("/api/refresh-token", summary="刷新访问令牌", tags=["认证"], response_model=APIResponse)
async def refresh_token(
    refresh_token: str,
    user_service = Depends(get_user_service)
) -> APIResponse:
    """
    使用刷新令牌获取新的访问令牌

    - **refresh_token**: 刷新令牌
    """
    token_result = user_service.refresh_user_token(refresh_token)
    return create_success_response("令牌刷新成功", data=token_result)

@app.post("/api/register", summary="用户注册", tags=["认证"], response_model=APIResponse)
async def register(
    user_data: UserRegister,
    user_service = Depends(get_user_service)
) -> APIResponse:
    """
    用户注册

    - **username**: 用户名
    - **password**: 密码
    - **nickname**: 昵称（可选）
    - **email**: 邮箱（可选）
    """
    user_info = user_service.register_user(
        username=user_data.username,
        password=user_data.password,
        nickname=user_data.nickname
    )

    # TODO: 在服务层中实现用户初始化逻辑（预设类别、默认属性等）
    # 当前暂时在这里处理，后续重构到服务层

    return create_success_response("用户注册成功", data=user_info)


@app.post("/api/create-test-user", summary="创建测试用户", tags=["测试"], response_model=APIResponse)
async def create_test_user(user_service = Depends(get_user_service)) -> APIResponse:
    """创建测试用户（仅用于开发测试）"""
    try:
        user_info = user_service.register_user(
            username="test",
            password="test123",
            nickname="测试用户"
        )
        return create_success_response("测试用户创建成功", data=user_info)
    except Exception as e:
        return create_error_response(f"创建测试用户失败: {str(e)}", error_code="TEST_USER_CREATION_FAILED")

# ==================== 用户相关路由 ====================
@app.post("/api/logout", summary="用户登出", tags=["用户"], response_model=APIResponse)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    用户登出
    """
    # 记录登出事件
    logger.info(f"用户 {current_user['username']} 已登出")
    
    # 在实际应用中，可以在这里将令牌加入黑名单
    # 或记录登出日志到数据库
    
    return APIResponse(
        success=True,
        message="登出成功"
    )

@app.get("/api/user/profile", summary="获取用户资料", tags=["用户"], response_model=APIResponse)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取当前用户的完整资料
    """
    # 获取用户余额
    balance = db.get_user_balance(current_user["user_id"])
    
    # 获取用户资源
    resources = db.get_user_resources(current_user["user_id"])
    
    # 获取用户统计数据
    stats = db.get_user_stats(current_user["user_id"])
    
    return APIResponse(
        success=True,
        message="用户资料获取成功",
        data={
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "nickname": current_user["nickname"],
            "email": current_user["email"],
            "level": current_user["level"],
            "experience": current_user.get("experience", 0),
            "balance": balance,
            "resources": resources,
            "stats": stats,
            "last_login": current_user["last_login"],
            "created_at": current_user["created_at"],
            "role": current_user["role"]
        }
    )

@app.put("/api/user/profile", summary="更新用户资料", tags=["用户"], response_model=APIResponse)
async def update_user_profile(
    nickname: Optional[str] = None,
    email: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    更新用户资料
    """
    if email:
        # 检查邮箱是否已被其他用户使用
        existing_user = db.get_user_by_email(email)
        if existing_user and existing_user["user_id"] != current_user["user_id"]:
            raise VoidSystemException(
                message="邮箱已被其他用户使用",
                error_code="EMAIL_IN_USE",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    success = db.update_user_profile(
        user_id=current_user["user_id"],
        nickname=nickname,
        email=email
    )
    
    if not success:
        raise VoidSystemException(
            message="资料更新失败",
            error_code="PROFILE_UPDATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="用户资料更新成功"
    )

# ==================== 属性系统相关路由 ====================
@app.get("/api/attributes", summary="获取用户属性列表", tags=["属性"], response_model=APIResponse)
async def get_attributes(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户所有属性
    """
    attributes = db.get_user_attributes(current_user["user_id"])
    
    # 添加调试日志，记录属性数量
    logger.debug(f"属性列表获取成功: 用户ID={current_user['user_id']}, 属性数量={len(attributes)}")
    
    # 直接返回属性列表，更符合前端期望
    return APIResponse(
        success=True,
        message="属性列表获取成功",
        data=attributes
    )

@app.post("/api/attributes", summary="创建新属性", tags=["属性"], response_model=APIResponse)
async def create_attribute(
    attribute_data: AttributeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    创建新属性
    """
    # 检查属性名是否已存在
    existing_attrs = db.get_user_attributes(current_user["user_id"])
    for attr in existing_attrs:
        if attr["attr_name"] == attribute_data.attr_name:
            raise VoidSystemException(
                message="属性名已存在",
                error_code="ATTRIBUTE_EXISTS",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    attr_id = db.add_attribute(
        user_id=current_user["user_id"],
        attr_name=attribute_data.attr_name,
        max_value=attribute_data.max_value,
        description=attribute_data.description or "",
        icon=attribute_data.icon or "📊"
    )
    
    if not attr_id:
        raise VoidSystemException(
            message="属性创建失败",
            error_code="ATTRIBUTE_CREATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # 创建成功后，获取完整的属性对象
    new_attributes = db.get_user_attributes(current_user["user_id"])
    new_attribute = next((attr for attr in new_attributes if attr["attr_id"] == attr_id), None)
    
    # 添加调试日志
    logger.debug(f"属性创建成功: 属性ID={attr_id}, 属性名={attribute_data.attr_name}, 是否获取到完整对象={new_attribute is not None}")
    
    # 返回完整的属性对象，前端可以直接添加到列表中
    return APIResponse(
        success=True,
        message="属性创建成功",
        data=new_attribute
    )

@app.put("/api/attributes/{attr_id}", summary="更新属性", tags=["属性"], response_model=APIResponse)
async def update_attribute(
    attr_id: str,
    attribute_data: AttributeUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    更新属性
    """
    # 验证属性归属
    attributes = db.get_user_attributes(current_user["user_id"])
    attribute = next(
        (attr for attr in attributes if attr["attr_id"] == attr_id),
        None
    )
    
    if not attribute:
        raise VoidSystemException(
            message="属性不存在或无权访问",
            error_code="ATTRIBUTE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 如果更新属性值，确保不超过最大值
    if attribute_data.attr_value is not None:
        max_value = attribute_data.max_value or attribute["max_value"]
        if attribute_data.attr_value > max_value:
            attribute_data.attr_value = max_value
    
    success = db.update_attribute(
        attr_id=attr_id,
        attr_value=attribute_data.attr_value,
        description=attribute_data.description,
        max_value=attribute_data.max_value
    )
    
    if not success:
        raise VoidSystemException(
            message="属性更新失败",
            error_code="ATTRIBUTE_UPDATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="属性更新成功"
    )

@app.delete("/api/attributes/{attr_id}", summary="删除属性", tags=["属性"], response_model=APIResponse)
async def delete_attribute(
    attr_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    删除属性
    """
    # 验证属性归属
    attributes = db.get_user_attributes(current_user["user_id"])
    attribute = next(
        (attr for attr in attributes if attr["attr_id"] == attr_id),
        None
    )
    
    if not attribute:
        raise VoidSystemException(
            message="属性不存在或无权访问",
            error_code="ATTRIBUTE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    success = db.delete_attribute(attr_id)
    
    if not success:
        raise VoidSystemException(
            message="属性删除失败",
            error_code="ATTRIBUTE_DELETE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="属性删除成功"
    )

# ==================== 任务系统相关路由 ====================
@app.post("/api/tasks", summary="创建新任务", tags=["任务"], response_model=APIResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    创建新任务
    """
    try:
        logger.info(f"用户 {current_user['username']} 创建任务: {task_data.task_name}")
        
        # 验证类别（如果提供了类别ID）
        if task_data.category_id:
            categories = db.get_user_task_categories(current_user["user_id"])
            category = next(
                (cat for cat in categories if cat["category_id"] == task_data.category_id),
                None
            )
            if not category:
                raise VoidSystemException(
                    message="任务类别不存在",
                    error_code="CATEGORY_NOT_FOUND",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # 使用正确的数据库方法名 add_task
        task_id = db.add_task(
            user_id=current_user["user_id"],
            task_name=task_data.task_name,
            description=task_data.description or "",
            related_attrs=task_data.related_attrs or {},
            estimated_time=task_data.estimated_time or 30,
            reward_coins=task_data.reward_coins or 10,
            category_id=task_data.category_id
        )
        
        return APIResponse(
            success=True,
            message="任务创建成功",
            data={"task_id": task_id}
        )
    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise VoidSystemException(
            message="任务创建失败",
            error_code="TASK_CREATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/tasks", summary="获取任务列表", tags=["任务"], response_model=APIResponse)
async def get_tasks(
    status: Optional[str] = None,
    category_id: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户任务列表
    """
    tasks = db.get_user_tasks(
        user_id=current_user["user_id"],
        task_status=status,
        category_id=category_id,
        limit=limit,
        offset=offset
    )
    
    # 获取任务统计
    task_stats = db.get_task_stats(current_user["user_id"])
    
    return APIResponse(
        success=True,
        message="任务列表获取成功",
        data={
            "tasks": tasks,
            "stats": task_stats,
            "pagination": {
                "total": len(tasks),
                "limit": limit,
                "offset": offset
            }
        }
    )

@app.get("/api/tasks/{task_id}", summary="获取任务详情", tags=["任务"], response_model=APIResponse)
async def get_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取任务详情
    """
    # 获取用户所有任务，然后查找特定任务
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise VoidSystemException(
            message="任务不存在或无权访问",
            error_code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return APIResponse(
        success=True,
        message="任务详情获取成功",
        data={"task": task}
    )

@app.put("/api/tasks/{task_id}/status", summary="更新任务状态", tags=["任务"], response_model=APIResponse)
async def update_task_status(
    task_id: str,
    new_status: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    更新任务状态
    """
    # 验证状态值
    valid_statuses = ['pending', 'in_progress', 'completed', 'failed']
    if new_status not in valid_statuses:
        raise VoidSystemException(
            message=f"状态值无效。必须是: {', '.join(valid_statuses)}",
            error_code="INVALID_STATUS",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # 先获取任务信息，检查归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise VoidSystemException(
            message="任务不存在或无权访问",
            error_code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 如果状态变为completed，发放奖励
    if new_status == 'completed' and task['status'] != 'completed':
        try:
            # 发放系统币奖励
            db.add_coins(
                user_id=current_user["user_id"],
                amount=task['reward_coins'],
                source=f"task_{task_id}_complete"
            )
            
            # 发放经验值
            experience = max(1, task['reward_coins'] // 2)
            db.add_experience(
                user_id=current_user["user_id"],
                amount=experience,
                source=f"task_{task_id}_complete"
            )
            
            # 如果有关联属性，根据任务完成情况更新属性值
            if task['related_attrs']:
                for attr_id, weight in task['related_attrs'].items():
                    # 计算属性增加值
                    attr_increase = max(1, int(weight * task['estimated_time'] / 60))
                    
                    # 获取当前属性值
                    attributes = db.get_user_attributes(current_user["user_id"])
                    attr = next(
                        (a for a in attributes if a["attr_id"] == attr_id),
                        None
                    )
                    if attr:
                        new_value = min(
                            attr['attr_value'] + attr_increase,
                            attr['max_value']
                        )
                        db.update_attribute_value(attr_id, new_value)
        except Exception as e:
            logger.error(f"发放任务奖励失败: {e}")
    
    success = db.update_task_status(task_id, current_user["user_id"], new_status)
    
    if not success:
        raise VoidSystemException(
            message="任务状态更新失败",
            error_code="TASK_STATUS_UPDATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="任务状态更新成功"
    )

@app.post("/api/tasks/{task_id}/proof", summary="提交任务证明", tags=["任务"], response_model=APIResponse)
async def submit_task_proof(
    task_id: str,
    proof_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    提交任务证明
    """
    # 先检查任务归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise VoidSystemException(
            message="任务不存在或无权访问",
            error_code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 验证任务状态
    if task['status'] == 'completed':
        raise VoidSystemException(
            message="任务已完成，无法提交证明",
            error_code="TASK_ALREADY_COMPLETED",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    success = db.submit_task_proof(
        task_id,
        current_user["user_id"],
        proof_data
    )
    
    if not success:
        raise VoidSystemException(
            message="任务证明提交失败",
            error_code="TASK_PROOF_SUBMIT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="任务证明提交成功"
    )

@app.post("/api/tasks/{task_id}/evaluate", summary="评估任务", tags=["任务"], response_model=APIResponse)
async def evaluate_task(
    task_id: str,
    evaluation_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    评估任务
    """
    # 先检查任务归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise VoidSystemException(
            message="任务不存在或无权访问",
            error_code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    success = db.update_task_evaluation(
        task_id,
        current_user["user_id"],
        self_evaluation=evaluation_data.get("self_evaluation"),
        ai_suggestion=evaluation_data.get("ai_suggestion")
    )
    
    if not success:
        raise VoidSystemException(
            message="任务评估更新失败",
            error_code="TASK_EVALUATION_UPDATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="任务评估更新成功"
    )

@app.delete("/api/tasks/{task_id}", summary="删除任务", tags=["任务"], response_model=APIResponse)
async def delete_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    删除任务
    """
    # 先检查任务归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise VoidSystemException(
            message="任务不存在或无权访问",
            error_code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 检查任务状态，已完成的任务不能删除
    if task['status'] == 'completed':
        raise VoidSystemException(
            message="已完成的任务不能删除",
            error_code="TASK_ALREADY_COMPLETED",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    success = db.delete_task(task_id)
    
    if not success:
        raise VoidSystemException(
            message="任务删除失败",
            error_code="TASK_DELETE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return APIResponse(
        success=True,
        message="任务删除成功"
    )

# ==================== 商店系统相关路由 ====================
@app.get("/api/shop/items", summary="获取商店商品列表", tags=["商店"], response_model=APIResponse)
async def get_shop_items(
    category: Optional[str] = None,
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取商店商品列表
    """
    # 从数据库获取商品列表（如果数据库支持）
    shop_items = [
        {
            "item_id": "item_energy_small",
            "item_name": "小型能量药水",
            "price": 50,
            "category": "consumable",
            "description": "恢复10点属性值",
            "icon": "🧪",
            "effect": {"attr_restore": 10}
        },
        {
            "item_id": "item_energy_medium",
            "item_name": "中型能量药水",
            "price": 150,
            "category": "consumable",
            "description": "恢复30点属性值",
            "icon": "🧪",
            "effect": {"attr_restore": 30}
        },
        {
            "item_id": "item_energy_large",
            "item_name": "大型能量药水",
            "price": 300,
            "category": "consumable",
            "description": "恢复50点属性值",
            "icon": "🧪",
            "effect": {"attr_restore": 50}
        },
        {
            "item_id": "item_task_accelerator",
            "item_name": "任务加速器",
            "price": 200,
            "category": "tool",
            "description": "减少任务完成时间20%",
            "icon": "⚡",
            "effect": {"task_time_reduction": 0.2}
        },
        {
            "item_id": "item_coin_detector",
            "item_name": "金币探测器",
            "price": 350,
            "category": "tool",
            "description": "增加任务奖励金币15%",
            "icon": "💰",
            "effect": {"coin_bonus": 0.15}
        },
        {
            "item_id": "item_experience_boost",
            "item_name": "经验加速器",
            "price": 250,
            "category": "tool",
            "description": "增加获得经验值20%",
            "icon": "🚀",
            "effect": {"exp_bonus": 0.2}
        }
    ]
    
    # 按类别筛选
    if category:
        shop_items = [item for item in shop_items if item["category"] == category]
    
    return APIResponse(
        success=True,
        message="商品列表获取成功",
        data={"items": shop_items}
    )

@app.post("/api/shop/purchase/{item_id}", summary="购买商品", tags=["商店"], response_model=APIResponse)
async def purchase_item(
    item_id: str,
    purchase_data: PurchaseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    购买商品
    """
    # 获取用户余额
    balance = db.get_user_balance(current_user["user_id"])
    
    # 商品数据
    shop_items: Dict[str, Dict[str, Any]] = {
        "item_energy_small": {"price": 50, "item_name": "小型能量药水", "effect": {"attr_restore": 10}},
        "item_energy_medium": {"price": 150, "item_name": "中型能量药水", "effect": {"attr_restore": 30}},
        "item_energy_large": {"price": 300, "item_name": "大型能量药水", "effect": {"attr_restore": 50}},
        "item_task_accelerator": {"price": 200, "item_name": "任务加速器", "effect": {"task_time_reduction": 0.2}},
        "item_coin_detector": {"price": 350, "item_name": "金币探测器", "effect": {"coin_bonus": 0.15}},
        "item_experience_boost": {"price": 250, "item_name": "经验加速器", "effect": {"exp_bonus": 0.2}}
    }
    
    # 检查商品是否存在
    if item_id not in shop_items:
        raise VoidSystemException(
            message="商品不存在",
            error_code="ITEM_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    item = shop_items[item_id]
    total_price = item["price"] * purchase_data.quantity
    
    # 检查余额是否充足
    if balance < total_price:
        raise VoidSystemException(
            message="余额不足",
            error_code="INSUFFICIENT_BALANCE",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # 扣款
    if not db.spend_coins(current_user["user_id"], total_price):
        raise VoidSystemException(
            message="扣款失败",
            error_code="PAYMENT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # 将购买的商品添加到用户资源
    resource_key = f"shop_{item_id}"
    if not db.add_user_resource(current_user["user_id"], resource_key, purchase_data.quantity):
        # 如果添加失败，退款
        db.add_coins(current_user["user_id"], total_price, source="purchase_refund")
        raise VoidSystemException(
            message="商品添加失败",
            error_code="ITEM_ADD_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # 记录购买历史
    db.record_purchase(
        user_id=current_user["user_id"],
        item_id=item_id,
        item_name=item["item_name"],
        quantity=purchase_data.quantity,
        total_price=total_price
    )
    
    return APIResponse(
        success=True,
        message="购买成功",
        data={
            "item_id": item_id,
            "item_name": item["item_name"],
            "quantity": purchase_data.quantity,
            "total_price": total_price,
            "remaining_balance": db.get_user_balance(current_user["user_id"])
        }
    )

# ==================== 任务类别相关路由 ====================
@app.get("/api/task-categories", summary="获取任务类别列表", tags=["任务类别"], response_model=APIResponse)
async def get_task_categories(
    include_preset: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户的任务类别列表
    """
    categories = db.get_user_task_categories(
        user_id=current_user["user_id"],
        include_preset=include_preset
    )
    
    return APIResponse(
        success=True,
        message="任务类别列表获取成功",
        data={"categories": categories}
    )

@app.post("/api/task-categories", summary="创建任务类别", tags=["任务类别"], response_model=APIResponse)
async def create_task_category(
    category_data: TaskCategoryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    创建新的任务类别
    """
    # 检查类别名是否已存在
    categories = db.get_user_task_categories(current_user["user_id"])
    for cat in categories:
        if cat["category_name"] == category_data.category_name:
            raise VoidSystemException(
                message="类别名已存在",
                error_code="CATEGORY_EXISTS",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    category_id = db.add_task_category(
        user_id=current_user["user_id"],
        category_name=category_data.category_name,
        description=category_data.description or "",
        icon=category_data.icon or "📚",
        color=category_data.color or "#3B82F6"
    )
    
    return APIResponse(
        success=True,
        message="任务类别创建成功",
        data={"category_id": category_id}
    )

@app.put("/api/task-categories/{category_id}", summary="更新任务类别", tags=["任务类别"], response_model=APIResponse)
async def update_task_category(
    category_id: str,
    category_data: TaskCategoryUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    更新任务类别
    """
    success = db.update_task_category(
        category_id=category_id,
        user_id=current_user["user_id"],
        category_name=category_data.category_name,
        description=category_data.description,
        icon=category_data.icon,
        color=category_data.color
    )
    
    if not success:
        raise VoidSystemException(
            message="任务类别不存在或无权访问",
            error_code="CATEGORY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return APIResponse(
        success=True,
        message="任务类别更新成功"
    )

@app.delete("/api/task-categories/{category_id}", summary="删除任务类别", tags=["任务类别"], response_model=APIResponse)
async def delete_task_category(
    category_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    删除任务类别
    """
    success = db.delete_task_category(
        category_id=category_id,
        user_id=current_user["user_id"]
    )
    
    if not success:
        raise VoidSystemException(
            message="任务类别不存在或无权删除",
            error_code="CATEGORY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return APIResponse(
        success=True,
        message="任务类别删除成功"
    )

# ==================== 统计分析路由 ====================
@app.get("/api/stats/overview", summary="获取统计概览", tags=["统计"], response_model=APIResponse)
async def get_stats_overview(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户统计概览
    """
    # 获取用户基本统计
    user_stats = db.get_user_stats(current_user["user_id"])

    # 获取任务统计
    task_stats = db.get_task_stats(current_user["user_id"])

    # 获取属性统计
    attributes = db.get_user_attributes(current_user["user_id"])
    attr_stats = {
        "total_attributes": len(attributes),
        "average_value": sum(attr["attr_value"] for attr in attributes) / len(attributes) if attributes else 0,
        "max_value_attr": max(attributes, key=lambda x: x["attr_value"]) if attributes else None
    }

    # 获取收入支出统计
    income_expense = db.get_income_expense_stats(current_user["user_id"])

    return APIResponse(
        success=True,
        message="统计概览获取成功",
        data={
            "user_stats": user_stats,
            "task_stats": task_stats,
            "attribute_stats": attr_stats,
            "income_expense": income_expense,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ==================== 管理员数据可视化路由 ====================
@app.get("/api/admin/visualization/overview", summary="获取系统数据可视化概览", tags=["数据可视化"], response_model=APIResponse)
async def get_visualization_overview(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取系统全局数据可视化概览（仅管理员）
    """
    try:
        # 用户统计
        user_stats = db.get_global_user_stats()

        # 任务统计
        task_stats = db.get_global_task_stats()

        # 属性统计
        attribute_stats = db.get_global_attribute_stats()

        # 经济统计
        economy_stats = db.get_global_economy_stats()

        # 文档统计
        document_stats = db.get_global_document_stats()

        return APIResponse(
            success=True,
            message="系统数据可视化概览获取成功",
            data={
                "user_stats": user_stats,
                "task_stats": task_stats,
                "attribute_stats": attribute_stats,
                "economy_stats": economy_stats,
                "document_stats": document_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    except Exception as e:
        logger.error(f"获取系统可视化概览失败: {e}")
        raise VoidSystemException(
            message="获取系统可视化概览失败",
            error_code="VISUALIZATION_OVERVIEW_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/admin/visualization/users", summary="获取用户数据统计", tags=["数据可视化"], response_model=APIResponse)
async def get_users_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户注册和活跃度统计（仅管理员）
    """
    try:
        # 用户注册趋势
        registration_trend = db.get_user_registration_trend(days)

        # 用户活跃度统计
        activity_stats = db.get_user_activity_stats(days)

        # 用户等级分布
        level_distribution = db.get_user_level_distribution()

        return APIResponse(
            success=True,
            message="用户数据统计获取成功",
            data={
                "registration_trend": registration_trend,
                "activity_stats": activity_stats,
                "level_distribution": level_distribution,
                "period_days": days
            }
        )
    except Exception as e:
        logger.error(f"获取用户可视化数据失败: {e}")
        raise VoidSystemException(
            message="获取用户可视化数据失败",
            error_code="USER_VISUALIZATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/admin/visualization/tasks", summary="获取任务数据统计", tags=["数据可视化"], response_model=APIResponse)
async def get_tasks_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取任务完成情况统计（仅管理员）
    """
    try:
        # 任务状态分布
        task_status_distribution = db.get_task_status_distribution()

        # 任务完成趋势
        completion_trend = db.get_task_completion_trend(days)

        # 任务类别统计
        category_stats = db.get_task_category_stats()

        # 平均任务耗时统计
        duration_stats = db.get_task_duration_stats()

        return APIResponse(
            success=True,
            message="任务数据统计获取成功",
            data={
                "status_distribution": task_status_distribution,
                "completion_trend": completion_trend,
                "category_stats": category_stats,
                "duration_stats": duration_stats,
                "period_days": days
            }
        )
    except Exception as e:
        logger.error(f"获取任务可视化数据失败: {e}")
        raise VoidSystemException(
            message="获取任务可视化数据失败",
            error_code="TASK_VISUALIZATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/admin/visualization/attributes", summary="获取属性数据统计", tags=["数据可视化"], response_model=APIResponse)
async def get_attributes_visualization(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取属性数据统计（仅管理员）
    """
    try:
        # 属性类型分布
        attribute_type_distribution = db.get_attribute_type_distribution()

        # 属性值分布统计
        attribute_value_distribution = db.get_attribute_value_distribution()

        # 最受欢迎的属性
        popular_attributes = db.get_popular_attributes(limit=10)

        return APIResponse(
            success=True,
            message="属性数据统计获取成功",
            data={
                "type_distribution": attribute_type_distribution,
                "value_distribution": attribute_value_distribution,
                "popular_attributes": popular_attributes
            }
        )
    except Exception as e:
        logger.error(f"获取属性可视化数据失败: {e}")
        raise VoidSystemException(
            message="获取属性可视化数据失败",
            error_code="ATTRIBUTE_VISUALIZATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/admin/visualization/economy", summary="获取经济数据统计", tags=["数据可视化"], response_model=APIResponse)
async def get_economy_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取经济数据统计（仅管理员）
    """
    try:
        # 系统币收支趋势
        coin_transaction_trend = db.get_coin_transaction_trend(days)

        # 用户余额分布
        balance_distribution = db.get_user_balance_distribution()

        # 商品销售统计
        item_sales_stats = db.get_item_sales_stats()

        # 经济健康度指标
        economy_health_metrics = db.get_economy_health_metrics()

        return APIResponse(
            success=True,
            message="经济数据统计获取成功",
            data={
                "transaction_trend": coin_transaction_trend,
                "balance_distribution": balance_distribution,
                "item_sales_stats": item_sales_stats,
                "health_metrics": economy_health_metrics,
                "period_days": days
            }
        )
    except Exception as e:
        logger.error(f"获取经济可视化数据失败: {e}")
        raise VoidSystemException(
            message="获取经济可视化数据失败",
            error_code="ECONOMY_VISUALIZATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== RAG文档管理路由 ====================
# ... existing code ...

# ==================== 用户文档管理路由 ====================
@app.get("/api/admin/rag/documents", summary="列出系统RAG文档", tags=["RAG管理"], response_model=APIResponse)
async def list_rag_documents(
    tags: Optional[str] = None,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    列出系统RAG文档（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        rag_manager = SystemRAGManager()
        filter_tags = tags.split(",") if tags else None
        result = rag_manager.list_documents(filter_tags)
        
        return APIResponse(
            success=result["success"],
            message=result.get("message", "列出RAG文档成功"),
            data={
                "documents": result["documents"],
                "count": result["count"]
            }
        )
    except Exception as e:
        logger.error(f"列出RAG文档失败: {e}")
        raise VoidSystemException(
            message=f"列出RAG文档失败: {str(e)}",
            error_code="RAG_LIST_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post("/api/admin/rag/documents", summary="上传系统RAG文档", tags=["RAG管理"], response_model=APIResponse)
async def upload_rag_document(
    request: Request,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    上传系统RAG文档（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        form = await request.form()
        file = form["file"]
        title = form.get("title", file.filename)
        tags = form.get("tags", "")
        description = form.get("description", "")
        
        # 保存临时文件
        temp_file_path = f"temp_{uuid.uuid4()}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        
        # 调用RAG管理器添加文档
        rag_manager = SystemRAGManager()
        result = rag_manager.add_document_to_system(
            file_path=temp_file_path,
            metadata={
                "title": title,
                "uploaded_by": current_admin["user_id"],
                "tags": tags.split(",") if tags else [],
                "description": description
            }
        )
        
        # 删除临时文件
        import os
        os.remove(temp_file_path)
        
        # 根据结果返回不同的响应
        if result["success"]:
            return APIResponse(
                success=True,
                message=result["message"],
                data={
                    "doc_id": result["doc_id"],
                    "chroma_ids_count": result["chroma_ids_count"]
                }
            )
        else:
            return APIResponse(
                success=False,
                message=result["message"]
            )
    except Exception as e:
        logger.error(f"上传RAG文档失败: {e}")
        raise VoidSystemException(
            message=f"上传RAG文档失败: {str(e)}",
            error_code="RAG_UPLOAD_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/admin/rag/documents/{doc_id}", summary="获取RAG文档详情", tags=["RAG管理"], response_model=APIResponse)
async def get_rag_document(
    doc_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    获取单个RAG文档详情（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        rag_manager = SystemRAGManager()
        result = rag_manager.get_document(doc_id)
        
        return APIResponse(
            success=result["success"],
            message=result.get("message", "获取RAG文档成功"),
            data={
                "document": result["document"]
            }
        )
    except Exception as e:
        logger.error(f"获取RAG文档失败: {e}")
        raise VoidSystemException(
            message=f"获取RAG文档失败: {str(e)}",
            error_code="RAG_GET_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.put("/api/admin/rag/documents/{doc_id}", summary="更新RAG文档", tags=["RAG管理"], response_model=APIResponse)
async def update_rag_document(
    doc_id: str,
    updates: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    更新RAG文档元数据（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        rag_manager = SystemRAGManager()
        result = rag_manager.update_document(doc_id, updates)
        
        return APIResponse(
            success=result["success"],
            message=result.get("message", "更新RAG文档成功")
        )
    except Exception as e:
        logger.error(f"更新RAG文档失败: {e}")
        raise VoidSystemException(
            message=f"更新RAG文档失败: {str(e)}",
            error_code="RAG_UPDATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.delete("/api/admin/rag/documents/{doc_id}", summary="删除RAG文档", tags=["RAG管理"], response_model=APIResponse)
async def delete_rag_document(
    doc_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    删除RAG文档（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        rag_manager = SystemRAGManager()
        result = rag_manager.delete_document(doc_id)
        
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        logger.error(f"删除RAG文档失败: {e}")
        raise VoidSystemException(
            message=f"删除RAG文档失败: {str(e)}",
            error_code="RAG_DELETE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post("/api/admin/rag/sync", summary="同步Chroma与数据库", tags=["RAG管理"], response_model=APIResponse)
async def sync_rag_db(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
) -> APIResponse:
    """
    同步Chroma向量库与SQLite数据库（仅管理员）
    """
    from services.ai_services.rag_manager import SystemRAGManager
    
    try:
        rag_manager = SystemRAGManager()
        result = rag_manager.sync_chroma_with_db()
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "deleted_ids_count": result["deleted_ids_count"]
            }
        )
    except Exception as e:
        logger.error(f"同步RAG数据库失败: {e}")
        raise VoidSystemException(
            message=f"同步RAG数据库失败: {str(e)}",
            error_code="RAG_SYNC_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== 用户文档管理路由 ====================
@app.post("/api/user/documents/upload", summary="上传用户文档", tags=["用户文档"])
async def upload_user_document(
    files: List[UploadFile] = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON字符串格式的标签数组
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    上传用户文档（支持多文件批量上传）
    DeepSeek风格的文件上传接口
    """
    from api.user_document_manager import document_manager

    try:
        if not files:
            raise VoidSystemException(
                message="请至少选择一个文件",
                error_code="NO_FILES",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 解析标签
        tag_list = []
        if tags:
            try:
                tag_list = json.loads(tags)
                if not isinstance(tag_list, list):
                    tag_list = []
            except json.JSONDecodeError:
                tag_list = []

        results = []
        for file in files:
            # 读取文件内容
            file_data = await file.read()

            # 调用文档管理器处理
            result = await document_manager.upload_and_process_document(
                user_id=current_user["user_id"],
                file_data=file_data,
                file_name=file.filename,
                title=title,
                tags=tag_list
            )

            results.append({
                "file_name": file.filename,
                **result
            })

        # 检查是否有成功上传的文件
        successful_uploads = [r for r in results if r.get("success")]

        if successful_uploads:
            return create_success_response(
                f"成功上传 {len(successful_uploads)}/{len(files)} 个文件",
                data={
                    "results": results,
                    "successful_count": len(successful_uploads),
                    "total_count": len(files)
                }
            )
        else:
            return create_error_response(
                "所有文件上传失败",
                error_code="UPLOAD_FAILED",
                data={"results": results}
            )

    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise VoidSystemException(
            message=f"文档上传失败: {str(e)}",
            error_code="UPLOAD_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/user/documents", summary="获取用户文档列表", tags=["用户文档"])
async def get_user_documents(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户文档列表
    支持状态筛选和分页
    """
    from api.user_document_manager import document_manager

    try:
        result = document_manager.get_user_documents(
            user_id=current_user["user_id"],
            status=status,
            limit=limit,
            offset=offset
        )

        return APIResponse(
            success=result["success"],
            message="获取文档列表成功" if result["success"] else result.get("message", "获取失败"),
            data=result
        )

    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise VoidSystemException(
            message=f"获取文档列表失败: {str(e)}",
            error_code="LIST_DOCUMENTS_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/user/documents/{doc_id}", summary="获取文档详情", tags=["用户文档"])
async def get_user_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取单个文档详情
    """
    from api.user_document_manager import document_manager

    try:
        result = document_manager.get_document(
            user_id=current_user["user_id"],
            doc_id=doc_id
        )

        if not result["success"]:
            raise VoidSystemException(
                message=result.get("message", "文档不存在"),
                error_code=result.get("error_code", "DOCUMENT_NOT_FOUND"),
                status_code=status.HTTP_404_NOT_FOUND
            )

        return APIResponse(
            success=True,
            message="获取文档详情成功",
            data=result["document"]
        )

    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {str(e)}")
        raise VoidSystemException(
            message=f"获取文档详情失败: {str(e)}",
            error_code="GET_DOCUMENT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.put("/api/user/documents/{doc_id}", summary="更新文档信息", tags=["用户文档"])
async def update_user_document(
    doc_id: str,
    title: Optional[str] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    更新文档基本信息
    """
    from api.user_document_manager import document_manager

    try:
        result = document_manager.update_document_info(
            user_id=current_user["user_id"],
            doc_id=doc_id,
            title=title,
            tags=tags
        )

        if not result["success"]:
            raise VoidSystemException(
                message=result.get("message", "文档不存在或无权访问"),
                error_code="DOCUMENT_UPDATE_FAILED",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return APIResponse(
            success=True,
            message="文档信息更新成功"
        )

    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"更新文档信息失败: {str(e)}")
        raise VoidSystemException(
            message=f"更新文档信息失败: {str(e)}",
            error_code="UPDATE_DOCUMENT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.delete("/api/user/documents/{doc_id}", summary="删除文档", tags=["用户文档"])
async def delete_user_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    删除用户文档
    """
    from api.user_document_manager import document_manager

    try:
        result = document_manager.delete_document(
            user_id=current_user["user_id"],
            doc_id=doc_id
        )

        if not result["success"]:
            raise VoidSystemException(
                message=result.get("message", "文档不存在或无权访问"),
                error_code="DOCUMENT_DELETE_FAILED",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return APIResponse(
            success=True,
            message="文档删除成功"
        )

    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise VoidSystemException(
            message=f"删除文档失败: {str(e)}",
            error_code="DELETE_DOCUMENT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/user/documents/stats", summary="获取文档统计", tags=["用户文档"])
async def get_user_document_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    获取用户文档统计信息
    """
    try:
        stats = db.get_user_document_stats(current_user["user_id"])

        return APIResponse(
            success=True,
            message="获取统计信息成功",
            data=stats
        )

    except Exception as e:
        logger.error(f"获取文档统计失败: {str(e)}")
        raise VoidSystemException(
            message=f"获取文档统计失败: {str(e)}",
            error_code="GET_STATS_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== 个性化问答路由 ====================
@app.post("/api/user/qa/ask", summary="基于文档智能问答", tags=["个性化问答"])
async def ask_with_user_documents(
    question: str = Body(..., embed=True),
    document_ids: Optional[List[str]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> APIResponse:
    """
    基于用户文档进行智能问答
    支持指定文档范围或自动检索相关文档
    """
    from api.personalized_qa import qa_engine

    try:
        if not question or not question.strip():
            raise VoidSystemException(
                message="问题不能为空",
                error_code="EMPTY_QUESTION",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 检查用户是否有可用的文档
        stats = db.get_user_document_stats(current_user["user_id"])
        if stats.get("completed_documents", 0) == 0:
            return APIResponse(
                success=True,
                message="问答功能需要您先上传文档",
                data={
                    "answer": "您还没有上传任何文档。请先上传相关文档，然后我就可以基于文档内容为您回答问题。",
                    "has_documents": False,
                    "stats": stats
                }
            )

        # 执行问答
        result = await qa_engine.answer_question(
            user_id=current_user["user_id"],
            question=question.strip(),
            selected_doc_ids=document_ids
        )

        if not result["success"]:
            raise VoidSystemException(
                message=result.get("answer", "问答处理失败"),
                error_code="QA_FAILED",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return APIResponse(
            success=True,
            message="问答完成",
            data={
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "confidence": result["confidence"],
                "retrieved_docs_count": result.get("retrieved_docs_count", 0),
                "has_documents": True,
                "stats": stats
            }
        )

    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"问答失败: {str(e)}")
        raise VoidSystemException(
            message=f"问答处理失败: {str(e)}",
            error_code="QA_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== 会话临时文件路由 ====================
@app.post("/api/session/new", summary="创建新会话", tags=["会话管理"], response_model=APIResponse)
async def create_new_session(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    创建新的会话
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        session_manager = SessionContextManager()
        result = session_manager.create_new_session(current_user["user_id"])
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "session_id": result["session_id"],
                "created_at": result["created_at"],
                "expires_in": result["expires_in"]
            }
        )
    except Exception as e:
        logger.error(f"创建新会话失败: {e}")
        raise VoidSystemException(
            message=f"创建新会话失败: {str(e)}",
            error_code="SESSION_CREATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post("/api/session/upload-temporary", summary="上传临时文件", tags=["会话管理"], response_model=APIResponse)
async def upload_temporary_file(
    request: Request,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    上传临时文件到会话
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        form = await request.form()
        file = form["file"]
        
        # 读取文件数据
        file_data = await file.read()
        
        # 调用会话管理器上传文件
        session_manager = SessionContextManager()
        result = session_manager.upload_temporary_file(
            user_id=current_user["user_id"],
            session_id=session_id,
            file_data=file_data,
            file_name=file.filename
        )
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "file_size": result["file_size"],
                "content_preview": result["content_preview"]
            }
        )
    except Exception as e:
        logger.error(f"上传临时文件失败: {e}")
        raise VoidSystemException(
            message=f"上传临时文件失败: {str(e)}",
            error_code="FILE_UPLOAD_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/session/context/{session_id}", summary="获取会话上下文", tags=["会话管理"], response_model=APIResponse)
async def get_session_context(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    获取会话上下文，包含临时文件
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        session_manager = SessionContextManager()
        result = session_manager.get_session_context(
            user_id=current_user["user_id"],
            session_id=session_id
        )
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "session_id": result["session_id"],
                "files": result["files"],
                "file_count": result["file_count"]
            }
        )
    except Exception as e:
        logger.error(f"获取会话上下文失败: {e}")
        raise VoidSystemException(
            message=f"获取会话上下文失败: {str(e)}",
            error_code="SESSION_CONTEXT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/session/active", summary="获取活跃会话", tags=["会话管理"], response_model=APIResponse)
async def get_active_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    获取用户的活跃会话列表
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        session_manager = SessionContextManager()
        result = session_manager.get_active_sessions(current_user["user_id"])
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "sessions": result["sessions"],
                "session_count": result["session_count"]
            }
        )
    except Exception as e:
        logger.error(f"获取活跃会话失败: {e}")
        raise VoidSystemException(
            message=f"获取活跃会话失败: {str(e)}",
            error_code="ACTIVE_SESSIONS_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/api/session/files/{file_id}", summary="获取临时文件内容", tags=["会话管理"], response_model=APIResponse)
async def get_temp_file_content(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    获取临时文件的内容预览
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        session_manager = SessionContextManager()
        result = session_manager.get_file_content(current_user["user_id"], file_id)
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data={
                "content_type": result["content_type"],
                "note": result["note"]
            }
        )
    except Exception as e:
        logger.error(f"获取临时文件内容失败: {e}")
        raise VoidSystemException(
            message=f"获取临时文件内容失败: {str(e)}",
            error_code="FILE_CONTENT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.delete("/api/session/files/{file_id}", summary="删除临时文件", tags=["会话管理"], response_model=APIResponse)
async def delete_temp_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> APIResponse:
    """
    删除会话中的临时文件
    """
    from api.session_context_manager import SessionContextManager
    
    try:
        session_manager = SessionContextManager()
        result = session_manager.delete_session_file(current_user["user_id"], file_id)
        
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        logger.error(f"删除临时文件失败: {e}")
        raise VoidSystemException(
            message=f"删除临时文件失败: {str(e)}",
            error_code="FILE_DELETE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== 应用启动 ====================
if __name__ == "__main__":
    # 检查必要的环境变量
    if not os.path.exists(".env"):
        logger.warning("⚠️ 未找到 .env 文件，使用默认配置")
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True
    )
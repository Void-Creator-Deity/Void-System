"""
Void System Backend - FastAPI Application
------------------------------------------
虚空系统后端主应用，提供用户认证、任务管理、属性系统、商店系统等核心功能。
集成 LangChain 服务，支持 AI 对话、知识问答和任务建议。
"""

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from langserve import add_routes
from typing import Any, Optional, List, Dict
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
import uvicorn
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta

from database import Database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("void-system")


# ==================== 全局配置 ====================
class Settings:
    """应用配置类"""
    SECRET_KEY = "your-secret-key-here-change-in-production"  # 生产环境必须修改
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    DATABASE_PATH = "void_system.db"


settings = Settings()

# 数据库实例
db = Database(settings.DATABASE_PATH)

# ==================== Pydantic 模型定义 ====================

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str


class UserRegister(BaseModel):
    """用户注册模型"""
    username: str
    password: str
    email: Optional[str] = None
    nickname: Optional[str] = None


class TaskCreate(BaseModel):
    """任务创建模型"""
    task_name: str
    description: Optional[str] = ""
    related_attrs: Optional[Dict[str, Any]] = None
    estimated_time: Optional[int] = 30
    reward_coins: Optional[int] = 10


class TaskUpdate(BaseModel):
    """任务更新模型"""
    status: Optional[str] = None
    proof_data: Optional[Dict[str, Any]] = None
    self_evaluation: Optional[Dict[str, Any]] = None


class AttributeCreate(BaseModel):
    """属性创建模型"""
    attr_name: str = Field(..., min_length=1, max_length=50)
    max_value: int = Field(default=100, ge=1, le=999)
    description: Optional[str] = ""


class AttributeUpdate(BaseModel):
    """属性更新模型"""
    attr_value: Optional[int] = None
    description: Optional[str] = None

# ==================== OAuth2 配置 ====================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    获取当前认证用户
    
    Args:
        token: JWT 令牌
        
    Returns:
        用户信息字典
        
    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

# ==================== FastAPI 应用初始化 ====================
app = FastAPI(
    title="Void System Core + LangServe",
    description="虚空系统后端 API，集成 LangChain 服务",
    version="0.1.0"
)

# 配置 CORS（允许前端跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 前端开发地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 LangChain 服务路由
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")
add_routes(app, load_persona_chain(), path="/lc/persona")

# ==================== 用户认证相关路由 ====================

@app.post("/token", summary="用户登录", tags=["认证"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最后登录时间
    db.update_last_login(user["user_id"])
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "level": user["level"]
    }

@app.post("/register", summary="用户注册", tags=["认证"])
async def register(user_data: UserRegister):
    # 检查用户名是否已存在
    existing_user = db.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 创建新用户
    password_hash = get_password_hash(user_data.password)
    user_id = db.add_user(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        nickname=user_data.nickname
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )
    
    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "username": user_data.username
    }

# ==================== 用户相关路由 ====================

@app.post("/logout", summary="用户登出", tags=["用户"])
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    # 记录退出登录事件（可选）
    logger.info(f"User {current_user['username']} logged out")
    
    # 对于JWT认证，主要在客户端删除token即可
    # 这里可以根据需要添加额外的登出逻辑，如：
    # 1. 将token加入黑名单（如果实现了token黑名单机制）
    # 2. 记录登出日志
    # 3. 其他清理工作
    
    return {
        "message": "Logged out successfully"
    }

@app.get("/user/profile", summary="获取用户资料", tags=["用户"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    # 获取用户余额
    balance = db.get_user_balance(current_user["user_id"])
    # 获取用户资源
    resources = db.get_user_resources(current_user["user_id"])
    
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "nickname": current_user["nickname"],
        "email": current_user["email"],
        "level": current_user["level"],
        "balance": balance,
        "resources": resources,
        "last_login": current_user["last_login"]
    }

# ==================== 属性系统相关路由 ====================

@app.get("/attributes", summary="获取用户属性列表", tags=["属性"])
async def get_attributes(current_user: Dict[str, Any] = Depends(get_current_user)):
    """获取用户所有属性"""
    attributes = db.get_user_attributes(current_user["user_id"])
    return attributes

@app.post("/attributes", summary="创建新属性", tags=["属性"])
async def create_attribute(
    attribute_data: AttributeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """创建新属性"""
    attr_id = db.add_attribute(
        user_id=current_user["user_id"],
        attr_name=attribute_data.attr_name,
        max_value=attribute_data.max_value,
        description=attribute_data.description
    )
    
    if not attr_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="属性创建失败"
        )
    
    return {
        "message": "属性创建成功",
        "attr_id": attr_id
    }

@app.put("/attributes/{attr_id}/value", summary="更新属性值", tags=["属性"])
async def update_attribute_value(
    attr_id: str,
    attr_value: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新属性值"""
    # 验证属性归属
    attributes = db.get_user_attributes(current_user["user_id"])
    attribute = next((attr for attr in attributes if attr["attr_id"] == attr_id), None)
    
    if not attribute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="属性不存在或无权访问"
        )
    
    # 更新属性值
    new_value = db.update_attribute_value(attr_id, attr_value)
    
    return {
        "message": "属性值更新成功",
        "attr_id": attr_id,
        "attr_value": new_value
    }

# ==================== 商店系统相关路由 ====================

@app.get("/shop/items", summary="获取商店商品列表", tags=["商店"])
async def get_shop_items():
    """获取商店商品列表"""
    # 由于数据库中没有商店表，暂时返回预设的商店商品
    shop_items = [
        {"item_id": "item1", "item_name": "小型能量药水", "price": 50, "category": "消耗品", "description": "恢复10点属性值"},
        {"item_id": "item2", "item_name": "中型能量药水", "price": 150, "category": "消耗品", "description": "恢复30点属性值"},
        {"item_id": "item3", "item_name": "大型能量药水", "price": 300, "category": "消耗品", "description": "恢复50点属性值"},
        {"item_id": "item4", "item_name": "任务加速器", "price": 200, "category": "工具", "description": "减少任务完成时间20%"},
        {"item_id": "item5", "item_name": "金币探测器", "price": 350, "category": "工具", "description": "增加任务奖励金币15%"}
    ]
    return shop_items

@app.post("/shop/purchase/{item_id}", summary="购买商品", tags=["商店"])
async def purchase_item(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """购买商品"""
    # 获取用户余额
    balance = db.get_user_balance(current_user["user_id"])
    
    # 模拟商品数据
    shop_items = {
        "item1": {"price": 50, "item_name": "小型能量药水"},
        "item2": {"price": 150, "item_name": "中型能量药水"},
        "item3": {"price": 300, "item_name": "大型能量药水"},
        "item4": {"price": 200, "item_name": "任务加速器"},
        "item5": {"price": 350, "item_name": "金币探测器"}
    }
    
    # 检查商品是否存在
    if item_id not in shop_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    item = shop_items[item_id]
    
    # 检查余额是否充足
    if balance < item["price"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="余额不足"
        )
    
    # 扣款
    if not db.spend_coins(current_user["user_id"], item["price"]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="扣款失败"
        )
    
    # 将购买的商品添加到用户资源
    if not db.add_user_resource(current_user["user_id"], item_id, 1):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="商品添加失败"
        )
    
    return {
        "message": "购买成功",
        "item_id": item_id,
        "item_name": item["item_name"],
        "price": item["price"],
        "remaining_balance": db.get_user_balance(current_user["user_id"])
    }

# ==================== 系统信息路由 ====================

@app.get("/", summary="系统状态", tags=["系统"])
def read_root():
    """系统根路径，返回系统状态"""
    return {"system": "VOID CORE ACTIVE", "status": "running"}


@app.get("/routes", summary="列出所有路由", tags=["系统"])
def list_routes():
    """列出所有可用的 API 路由"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path, 
                "methods": list(route.methods) if hasattr(route, "methods") else []
            })
    return routes


# ==================== 任务系统相关路由 ====================

@app.post("/tasks", summary="创建新任务", tags=["任务"])
async def create_task(
    task_data: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    task_id = db.create_task(
        user_id=current_user["user_id"],
        task_name=task_data.task_name,
        description=task_data.description,
        related_attrs=task_data.related_attrs,
        estimated_time=task_data.estimated_time,
        reward_coins=task_data.reward_coins
    )
    
    return {
        "message": "Task created successfully",
        "task_id": task_id
    }

@app.get("/tasks", summary="获取任务列表", tags=["任务"])
async def get_tasks(
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    tasks = db.get_user_tasks(current_user["user_id"], status)
    return tasks

@app.get("/tasks/{task_id}", summary="获取任务详情", tags=["任务"])
async def get_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # 获取用户所有任务，然后查找特定任务
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    return task

@app.put("/tasks/{task_id}/status", summary="更新任务状态", tags=["任务"])
async def update_task_status(
    task_id: str,
    status: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # 验证状态值
    valid_statuses = ['pending', 'in_progress', 'completed', 'failed']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # 先获取任务信息，检查归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    # 如果状态变为completed，发放奖励
    if status == 'completed' and task['status'] != 'completed':
        # 发放系统币奖励
        db.add_coins(
            user_id=current_user["user_id"],
            amount=task['reward_coins'],
            source=f"task_{task_id}_complete"
        )
        
        # 如果有关联属性，根据任务完成情况更新属性值
        if task['related_attrs']:
            for attr_id, weight in task['related_attrs'].items():
                # 简单策略：根据权重和任务难度计算属性增加值
                attr_increase = max(1, int(weight * task['estimated_time'] / 60))
                
                # 获取当前属性值
                attributes = db.get_user_attributes(current_user["user_id"])
                attr = next((a for a in attributes if a["attr_id"] == attr_id), None)
                if attr:
                    new_value = attr['attr_value'] + attr_increase
                    db.update_attribute_value(attr_id, new_value)
    
    success = db.update_task_status(task_id, current_user["user_id"], status)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update task status"
        )
    
    return {"message": "Task status updated successfully"}

@app.post("/tasks/{task_id}/proof", summary="提交任务证明", tags=["任务"])
async def submit_task_proof(
    task_id: str,
    proof_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # 先检查任务归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    success = db.submit_task_proof(task_id, current_user["user_id"], proof_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to submit task proof"
        )
    
    return {"message": "Task proof submitted successfully"}

@app.post("/tasks/{task_id}/evaluate", summary="评估任务", tags=["任务"])
async def evaluate_task(
    task_id: str,
    evaluation_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # 先检查任务归属
    tasks = db.get_user_tasks(current_user["user_id"])
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    success = db.update_task_evaluation(
        task_id,
        current_user["user_id"],
        self_evaluation=evaluation_data.get("self_evaluation"),
        ai_suggestion=evaluation_data.get("ai_suggestion")
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update task evaluation"
        )
    
    return {"message": "Task evaluation updated successfully"}


# ==================== 全局异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON 错误响应
    """
    logger.error(f"❌ 未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "系统内部错误", "detail": str(exc)}
    )


# ==================== 应用启动 ====================

if __name__ == "__main__":
    uvicorn.run(
        'main:app',
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True
    )
    logger.info("🚀 Void System Backend 已启动，监听端口 8000")
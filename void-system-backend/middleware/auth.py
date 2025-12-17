"""
Void System - Authentication Middleware
认证中间件，实现JWT令牌验证和用户权限检查
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt

from config import config
from errors import ErrorCode, VoidSystemException
from database import Database

logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Database = Depends(lambda: Database(config.get_database_path()))
) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息

    Args:
        token: JWT访问令牌
        db: 数据库实例

    Returns:
        用户信息字典，如果未认证返回None

    Raises:
        VoidSystemException: 令牌无效或过期
    """
    if not token:
        return None

    try:
        # 解码JWT令牌
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: str = payload.get("user_id")
        username: str = payload.get("sub")

        if user_id is None or username is None:
            raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)

        # 从数据库验证用户
        user = db.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

        # 检查用户是否激活
        if not user.get("is_active", True):
            raise VoidSystemException.from_error_code(ErrorCode.USER_INACTIVE)

        return user

    except JWTError as e:
        logger.warning(f"JWT解码失败: {e}")
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    except VoidSystemException:
        raise
    except Exception as e:
        logger.error(f"用户认证失败: {e}")
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)


def require_authentication(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    要求用户必须认证的依赖注入

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典

    Raises:
        VoidSystemException: 用户未认证
    """
    if current_user is None:
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_MISSING)

    return current_user


def require_admin_role(current_user: Dict[str, Any] = Depends(require_authentication)) -> Dict[str, Any]:
    """
    要求用户必须是管理员的依赖注入

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典

    Raises:
        VoidSystemException: 权限不足
    """
    if current_user.get("role") != "admin":
        raise VoidSystemException.from_error_code(
            ErrorCode.INSUFFICIENT_PERMISSIONS,
            details={"required_role": "admin", "user_role": current_user.get("role")}
        )

    return current_user


def create_access_token(data: Dict[str, Any]) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据

    Returns:
        JWT访问令牌
    """
    to_encode = data.copy()

    # 设置过期时间
    expire = data.get("exp")
    if not expire:
        expire = (data.get("expires_delta") or timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))

        if isinstance(expire, timedelta):
            expire = datetime.utcnow() + expire

        to_encode.update({"exp": expire})

    # 编码JWT
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建刷新令牌

    Args:
        data: 要编码的数据

    Returns:
        JWT刷新令牌
    """
    to_encode = data.copy()

    # 设置过期时间（更长）
    expire = data.get("exp")
    if not expire:
        expire_delta = timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)
        expire = datetime.utcnow() + expire_delta
        to_encode.update({"exp": expire})

    # 编码JWT
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        密码是否正确
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    Args:
        password: 明文密码

    Returns:
        密码哈希字符串
    """
    try:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except Exception as e:
        logger.error(f"密码哈希生成失败: {e}")
        raise VoidSystemException.from_error_code(
            ErrorCode.SYSTEM_ERROR,
            details={"operation": "password_hashing"}
        )


# 导入datetime（避免循环导入）
from datetime import datetime, timedelta
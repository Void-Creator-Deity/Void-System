"""
Void System - User Service
用户业务逻辑服务，实现用户注册、登录、信息管理等功能
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from config import config
from database import Database
from errors import ErrorCode, VoidSystemException, create_auth_error
from tools.utils import sanitize_string, get_current_timestamp
from middleware.auth import get_password_hash, verify_password, create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类"""

    def __init__(self, db: Database):
        """
        初始化用户服务

        Args:
            db: 数据库实例
        """
        self.db = db

    def register_user(self, email: str, password: str, username: str) -> Dict[str, Any]:
        """
        用户注册
        """
        # 清理输入
        username = sanitize_string(username, 50)
        email = sanitize_string(email, 100)
        password = sanitize_string(password, 100)
        
        # 检查邮箱是否已存在
        if self.db.get_user_by_email(email):
            raise VoidSystemException.from_error_code(ErrorCode.USER_ALREADY_EXISTS, details={"message": "该邮箱已注册"})
        
        # 检查用户名是否已存在
        if self.db.get_user_by_username(username):
             raise VoidSystemException.from_error_code(ErrorCode.USER_ALREADY_EXISTS, details={"message": "档案代号已存在"})
        
        # 创建密码哈希
        password_hash = get_password_hash(password)
        
        # 入库 (昵称同步为用户名)
        user_id = self.db.add_user(
            username=username,
            email=email,
            password_hash=password_hash
        )
        
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": "user"
        }
    

    def authenticate_user(self, identifier: str, password: str) -> Dict[str, Any]:
        """
        用户认证 (支持通过邮箱或用户名登录)
        """
        # 登录策略控制
        is_email = "@" in identifier
        
        user = None
        if is_email:
            # 1. 尝试邮箱登录 (普通用户标准)
            user = self.db.get_user_by_email(identifier)
        else:
            # 2. 尝试用户名登录 (管理员/特殊用户标准)
            user = self.db.get_user_by_username(identifier)
            if user and user.get("role") != "admin" and identifier != "test":
                # 非管理员禁止使用用户名登录
                raise VoidSystemException.from_error_code(
                    ErrorCode.INVALID_CREDENTIALS, 
                    details={"message": "普通账号请使用邮箱登录"}
                )
            
        if not user:
            raise create_auth_error(ErrorCode.INVALID_CREDENTIALS)

        # 验证密码
        if not verify_password(password, user["password_hash"]):
            raise create_auth_error(ErrorCode.INVALID_CREDENTIALS)

        # 检查用户状态
        if not user.get("is_active", True):
            raise create_auth_error(ErrorCode.USER_INACTIVE)

        # 更新最后登录时间
        self.db.update_last_login(user["user_id"])

        # 生成令牌
        access_token = create_access_token({
            "sub": user["user_id"],
            "username": user["username"]
        })

        refresh_token = create_refresh_token({
            "sub": user["user_id"],
            "username": user["username"]
        })

        logger.info(f"登录成功: {user['username']} ({user['email']})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "level": user.get("level", 1),
                "role": user["role"]
            }
        }

    def refresh_user_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        刷新用户访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            新令牌信息

        Raises:
            VoidSystemException: 令牌无效
        """
        try:
            from jose import jwt

            # 解码刷新令牌
            payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            sub: str = payload.get("sub")

            if not sub:
                raise create_auth_error(ErrorCode.TOKEN_INVALID)

            # 验证用户存在 (尝试作为ID，或作为用户名 fallback)
            user = self.db.get_user_by_id(sub)
            if not user:
                user = self.db.get_user_by_username(sub)
                
            if not user:
                raise create_auth_error(ErrorCode.USER_NOT_FOUND)

            # 生成新令牌
            new_access_token = create_access_token({
                "sub": user["user_id"],
                "username": user["username"]
            })

            logger.info(f"用户令牌刷新成功: {user['username']}")

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }

        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            raise create_auth_error(ErrorCode.TOKEN_INVALID)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户资料

        Args:
            user_id: 用户ID

        Returns:
            用户资料字典

        Raises:
            VoidSystemException: 用户不存在
        """
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

        # 移除敏感信息
        user_profile = user.copy()
        if "password_hash" in user_profile:
            del user_profile["password_hash"]

        return user_profile

    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户资料

        Args:
            user_id: 用户ID
            update_data: 更新数据

        Returns:
            更新后的用户资料

        Raises:
            VoidSystemException: 用户不存在或更新失败
        """
        # 验证用户存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

        # 清理输入数据
        allowed_fields = ["username"]
        cleaned_data = {}

        for field in allowed_fields:
            if field in update_data:
                value = update_data[field]
                if value is not None:
                    cleaned_data[field] = sanitize_string(str(value), 50)

        if not cleaned_data:
            raise VoidSystemException.from_error_code(
                ErrorCode.INVALID_REQUEST,
                details={"message": "没有有效的更新字段"}
            )

        # 更新数据库
        try:
            self.db.update_user(user_id, cleaned_data)

            # 获取更新后的用户资料
            updated_user = self.db.get_user_by_id(user_id)
            user_profile = updated_user.copy()
            if "password_hash" in user_profile:
                del user_profile["password_hash"]

            logger.info(f"用户资料更新成功: {user_id}")
            return user_profile

        except Exception as e:
            logger.error(f"用户资料更新失败: {user_id}, 错误: {e}")
            raise VoidSystemException.from_error_code(
                ErrorCode.SYSTEM_ERROR,
                details={"operation": "user_profile_update"}
            )

    def change_user_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        修改用户密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            修改是否成功

        Raises:
            VoidSystemException: 密码验证失败或修改失败
        """
        # 获取用户
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

        # 验证旧密码
        if not verify_password(old_password, user["password_hash"]):
            raise create_auth_error(ErrorCode.INVALID_CREDENTIALS)

        # 验证新密码
        if len(new_password) < 6:
            raise VoidSystemException.from_error_code(
                ErrorCode.INVALID_REQUEST,
                details={"message": "新密码长度至少6位"}
            )

        # 生成新密码哈希
        new_password_hash = get_password_hash(new_password)

        # 更新密码
        try:
            self.db.update_user(user_id, {"password_hash": new_password_hash})
            logger.info(f"用户密码修改成功: {user_id}")
            return True

        except Exception as e:
            logger.error(f"用户密码修改失败: {user_id}, 错误: {e}")
            raise VoidSystemException.from_error_code(
                ErrorCode.SYSTEM_ERROR,
                details={"operation": "password_change"}
            )

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息

        Args:
            user_id: 用户ID

        Returns:
            用户统计信息字典
        """
        try:
            # 获取用户基本信息
            user = self.db.get_user_by_id(user_id)
            if not user:
                raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

            # 从数据库获取详细统计
            db_stats = self.db.get_user_stats(user_id)

            stats = {
                "user_id": user_id,
                "level": user.get("level", 1),
                "experience": user.get("experience", 0),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login"),
                "documents_count": db_stats.get("total_documents", 0),
                "tasks_completed": db_stats.get("completed_tasks", 0),
                "tasks_total": db_stats.get("total_tasks", 0),
                "tasks_in_progress": db_stats.get("in_progress_tasks", 0),
                "completion_rate": db_stats.get("completion_rate", 0),
                "total_earned_coins": db_stats.get("total_earned_coins", 0),
                "total_spent_coins": db_stats.get("total_spent_coins", 0)
            }

            return stats

        except VoidSystemException:
            raise
        except Exception as e:
            logger.error(f"获取用户统计失败: {user_id}, 错误: {e}")
            raise VoidSystemException.from_error_code(
                ErrorCode.SYSTEM_ERROR,
                details={"operation": "user_stats"}
            )


# 全局用户服务实例
def get_user_service(db: Database = None) -> UserService:
    """获取用户服务实例"""
    if db is None:
        db = Database(config.get_database_path())
    return UserService(db)

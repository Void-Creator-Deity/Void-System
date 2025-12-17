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

    def register_user(self, username: str, password: str, nickname: str = None) -> Dict[str, Any]:
        """
        用户注册

        Args:
            username: 用户名
            password: 密码
            nickname: 昵称（可选）

        Returns:
            用户信息字典

        Raises:
            VoidSystemException: 用户已存在等错误
        """
        # 清理输入数据
        username = sanitize_string(username, 50)
        password = sanitize_string(password, 100)
        nickname = sanitize_string(nickname or username, 50)

        # 验证输入
        if not username or not password:
            raise VoidSystemException.from_error_code(
                ErrorCode.INVALID_REQUEST,
                details={"missing": ["username", "password"] if not username and not password else ["username"] if not username else ["password"]}
            )

        if len(password) < 6:
            raise VoidSystemException.from_error_code(
                ErrorCode.INVALID_REQUEST,
                details={"message": "密码长度至少6位"}
            )

        # 检查用户是否已存在
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_ALREADY_EXISTS)

        # 创建新用户
        try:
            # 生成密码哈希
            password_hash = get_password_hash(password)

            # 创建用户
            user_data = {
                "username": username,
                "password_hash": password_hash,
                "nickname": nickname,
                "level": 1,
                "experience": 0,
                "role": "user",
                "is_active": True,
                "created_at": get_current_timestamp(),
                "last_login": None
            }

            # 只传递add_user方法支持的参数
            user_id = self.db.add_user(
                username=user_data['username'],
                password_hash=user_data['password_hash'],
                nickname=user_data['nickname']
            )

            logger.info(f"用户注册成功: {username} (ID: {user_id})")

            # 返回用户信息（不包含密码）
            user_info = user_data.copy()
            del user_info["password_hash"]
            user_info["user_id"] = user_id

            return user_info

        except Exception as e:
            logger.error(f"用户注册失败: {username}, 错误: {e}")
            raise VoidSystemException.from_error_code(
                ErrorCode.SYSTEM_ERROR,
                details={"operation": "user_registration"}
            )

    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户认证

        Args:
            username: 用户名
            password: 密码

        Returns:
            认证结果字典

        Raises:
            VoidSystemException: 认证失败
        """
        # 清理输入
        username = sanitize_string(username, 50)
        password = sanitize_string(password, 100)

        # 获取用户
        user = self.db.get_user_by_username(username)
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
            "sub": user["username"],
            "user_id": user["user_id"]
        })

        refresh_token = create_refresh_token({
            "sub": user["username"],
            "user_id": user["user_id"]
        })

        logger.info(f"用户登录成功: {username}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "nickname": user["nickname"],
                "level": user["level"],
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
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")

            if not username or not user_id:
                raise create_auth_error(ErrorCode.TOKEN_INVALID)

            # 验证用户存在
            user = self.db.get_user_by_id(user_id)
            if not user:
                raise create_auth_error(ErrorCode.USER_NOT_FOUND)

            # 生成新令牌
            new_access_token = create_access_token({
                "sub": user["username"],
                "user_id": user["user_id"]
            })

            logger.info(f"用户令牌刷新成功: {username}")

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
        allowed_fields = ["nickname"]
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

            # TODO: 获取用户的文档数量、任务完成情况等统计信息
            # 这里可以扩展为更丰富的统计数据

            stats = {
                "user_id": user_id,
                "level": user.get("level", 1),
                "experience": user.get("experience", 0),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login"),
                # TODO: 添加文档统计、任务统计等
                "documents_count": 0,  # 待实现
                "tasks_completed": 0,   # 待实现
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

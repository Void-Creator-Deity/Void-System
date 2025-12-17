"""
Void System - Configuration Management
统一配置文件管理，实现前后端更好的解耦
"""
import os
import secrets
from typing import Optional
from pathlib import Path


class Config:
    """应用配置管理类"""

    # ==================== 基础配置 ====================
    # 项目根目录
    BASE_DIR: Path = Path(__file__).parent

    # 环境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ==================== 服务器配置 ====================
    # 服务器主机
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # 服务器端口
    PORT: int = int(os.getenv("PORT", "8000"))

    # 是否开启调试模式
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ==================== 数据库配置 ====================
    # 数据库文件路径
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///void_system.db")

    # 数据库连接池大小
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))

    # ==================== 认证配置 ====================
    # 生成安全的默认密钥（仅用于开发环境）
    _default_secret: str = secrets.token_urlsafe(32)
    # JWT密钥 - 使用环境变量或生成安全的随机密钥
    SECRET_KEY: str = os.getenv("SECRET_KEY", _default_secret)

    # JWT算法
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    # 访问令牌过期时间（分钟）
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # 刷新令牌过期时间（天）
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ==================== 文件上传配置 ====================
    # 最大文件大小 (50MB)
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS: set = {
        'txt', 'md', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
        'py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml'
    }

    # 用户文件存储目录
    USER_FILES_DIR: str = os.getenv("USER_FILES_DIR", "user_files")

    # ==================== AI配置 ====================
    # Ollama服务地址
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # 默认嵌入模型
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # 默认聊天模型
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "qwen2.5:7b")

    # ==================== 向量数据库配置 ====================
    # ChromaDB持久化目录
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")

    # 向量维度
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "384"))

    # ==================== 日志配置 ====================
    # 日志级别
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 日志文件路径
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/void_system.log")

    # ==================== 前端配置 ====================
    # CORS允许的源
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")

    # ==================== 任务系统配置 ====================
    # 最大任务并发数
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))

    # 任务队列大小
    TASK_QUEUE_SIZE: int = int(os.getenv("TASK_QUEUE_SIZE", "100"))

    # ==================== 缓存配置 ====================
    # Redis配置（预留）
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # 缓存过期时间（秒）
    CACHE_EXPIRE_SECONDS: int = int(os.getenv("CACHE_EXPIRE_SECONDS", "3600"))

    @classmethod
    def is_production(cls) -> bool:
        """判断是否为生产环境"""
        return cls.ENVIRONMENT.lower() == "production"

    @classmethod
    def is_development(cls) -> bool:
        """判断是否为开发环境"""
        return cls.ENVIRONMENT.lower() == "development"

    @classmethod
    def get_database_path(cls) -> str:
        """获取数据库文件路径"""
        if cls.DATABASE_URL.startswith("sqlite:///"):
            db_path = cls.DATABASE_URL.replace("sqlite:///", "")
            return str(cls.BASE_DIR / db_path)
        return cls.DATABASE_URL

    @classmethod
    def get_user_files_path(cls) -> Path:
        """获取用户文件存储路径"""
        return cls.BASE_DIR / cls.USER_FILES_DIR

    @classmethod
    def get_chroma_path(cls) -> Path:
        """获取ChromaDB存储路径"""
        return cls.BASE_DIR / cls.CHROMA_PERSIST_DIR


# ==================== 全局配置实例 ====================
config = Config()
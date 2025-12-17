"""
Void System - Utility Functions
通用工具函数，实现代码复用和解耦
"""
import os
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
import logging

from config import config
from errors import ErrorCode, VoidSystemException

logger = logging.getLogger(__name__)


# ==================== 文件处理工具 ====================

def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名

    Args:
        filename: 文件名

    Returns:
        文件扩展名（小写）
    """
    if '.' not in filename:
        return ''
    return filename.split('.')[-1].lower()


def is_allowed_file(filename: str) -> bool:
    """
    检查文件类型是否被允许

    Args:
        filename: 文件名

    Returns:
        是否允许上传
    """
    extension = get_file_extension(filename)
    return extension in config.ALLOWED_EXTENSIONS


def validate_file_size(file_size: int) -> None:
    """
    验证文件大小

    Args:
        file_size: 文件大小（字节）

    Raises:
        VoidSystemException: 文件过大
    """
    if file_size > config.MAX_FILE_SIZE:
        raise VoidSystemException.from_error_code(
            ErrorCode.FILE_TOO_LARGE,
            details={"max_size": config.MAX_FILE_SIZE, "actual_size": file_size}
        )


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一的文件名

    Args:
        original_filename: 原始文件名

    Returns:
        唯一文件名
    """
    extension = get_file_extension(original_filename)
    unique_id = str(uuid.uuid4())

    if extension:
        return f"{unique_id}.{extension}"
    return unique_id


def ensure_directory_exists(path: Path) -> None:
    """
    确保目录存在，如果不存在则创建

    Args:
        path: 目录路径
    """
    path.mkdir(parents=True, exist_ok=True)


def get_file_hash(file_data: bytes) -> str:
    """
    计算文件内容的MD5哈希值

    Args:
        file_data: 文件数据

    Returns:
        MD5哈希字符串
    """
    return hashlib.md5(file_data).hexdigest()


# ==================== 数据验证工具 ====================

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    验证必需字段是否存在

    Args:
        data: 数据字典
        required_fields: 必需字段列表

    Raises:
        VoidSystemException: 缺少必需字段
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise VoidSystemException.from_error_code(
            ErrorCode.INVALID_REQUEST,
            details={"missing_fields": missing_fields}
        )


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    清理字符串，移除危险字符

    Args:
        text: 原始字符串
        max_length: 最大长度限制

    Returns:
        清理后的字符串
    """
    if not text:
        return ""

    # 移除首尾空白字符
    text = text.strip()

    # 限制长度
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text


# ==================== 时间处理工具 ====================

def get_current_timestamp() -> datetime:
    """
    获取当前UTC时间戳

    Returns:
        当前时间
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime) -> str:
    """
    格式化日期时间为ISO字符串

    Args:
        dt: 日期时间对象

    Returns:
        ISO格式字符串
    """
    return dt.isoformat()


# ==================== 分页工具 ====================

def paginate_results(
    items: List[Any],
    page: int = 1,
    page_size: int = 10
) -> Dict[str, Any]:
    """
    对结果列表进行分页

    Args:
        items: 结果列表
        page: 页码（从1开始）
        page_size: 每页大小

    Returns:
        分页结果字典
    """
    total_count = len(items)
    total_pages = (total_count + page_size - 1) // page_size

    # 验证页码范围
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    return {
        "items": items[start_index:end_index],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ==================== 缓存工具 ====================

class SimpleCache:
    """简单的内存缓存实现"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回None
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 过期时间（秒），可选
        """
        self._cache[key] = {
            "value": value,
            "expires_at": get_current_timestamp().timestamp() + ttl_seconds if ttl_seconds else None
        }

    def delete(self, key: str) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的数量
        """
        current_time = get_current_timestamp().timestamp()
        expired_keys = [
            key for key, data in self._cache.items()
            if data.get("expires_at") and data["expires_at"] < current_time
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


# ==================== 全局缓存实例 ====================
cache = SimpleCache()


# ==================== 字符串处理工具 ====================

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    从文本中提取关键词（简单的实现）

    Args:
        text: 文本内容
        max_keywords: 最大关键词数量

    Returns:
        关键词列表
    """
    # 简单的关键词提取：移除常见停用词，获取最长的词
    stop_words = {'的', '了', '和', '是', '在', '有', '为', '这', '那', '一个', '可以', '使用'}

    words = []
    current_word = ""

    for char in text:
        if char.isalnum() or char in ('_', '-'):
            current_word += char
        else:
            if current_word and current_word not in stop_words and len(current_word) > 1:
                words.append(current_word)
            current_word = ""

    # 添加最后一个词
    if current_word and current_word not in stop_words and len(current_word) > 1:
        words.append(current_word)

    # 按长度排序，取前N个
    words.sort(key=len, reverse=True)
    return words[:max_keywords]


# ==================== 性能监控工具 ====================

def time_function_execution(func_name: str):
    """
    函数执行时间装饰器

    Args:
        func_name: 函数名（用于日志）

    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = get_current_timestamp()
            try:
                result = func(*args, **kwargs)
                end_time = get_current_timestamp()
                duration = (end_time - start_time).total_seconds()
                logger.debug(f"函数 {func_name} 执行时间: {duration:.3f}秒")
                return result
            except Exception as e:
                end_time = get_current_timestamp()
                duration = (end_time - start_time).total_seconds()
                logger.error(f"函数 {func_name} 执行失败，耗时: {duration:.3f}秒，错误: {e}")
                raise
        return wrapper
    return decorator

"""
Void System - Error Codes and Exceptions
统一错误码管理，实现更好的错误处理解耦
"""
from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """统一错误码枚举"""

    # ==================== 认证相关错误 ====================
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"           # 用户名或密码错误
    TOKEN_EXPIRED = "TOKEN_EXPIRED"                       # 令牌过期
    TOKEN_INVALID = "TOKEN_INVALID"                       # 令牌无效
    TOKEN_MISSING = "TOKEN_MISSING"                       # 缺少令牌
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS" # 权限不足

    # ==================== 用户相关错误 ====================
    USER_NOT_FOUND = "USER_NOT_FOUND"                     # 用户不存在
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"           # 用户已存在
    USER_INACTIVE = "USER_INACTIVE"                       # 用户未激活

    # ==================== 文件相关错误 ====================
    FILE_TOO_LARGE = "FILE_TOO_LARGE"                     # 文件过大
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"       # 文件类型不允许
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"             # 文件上传失败
    FILE_PROCESSING_FAILED = "FILE_PROCESSING_FAILED"     # 文件处理失败
    FILE_NOT_FOUND = "FILE_NOT_FOUND"                     # 文件不存在
    NO_FILES = "NO_FILES"                                 # 没有文件

    # ==================== 数据库相关错误 ====================
    DATABASE_ERROR = "DATABASE_ERROR"                     # 数据库错误
    DATA_NOT_FOUND = "DATA_NOT_FOUND"                     # 数据不存在
    DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED"     # 数据验证失败

    # ==================== AI/向量相关错误 ====================
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"     # AI服务不可用
    VECTOR_SEARCH_FAILED = "VECTOR_SEARCH_FAILED"         # 向量搜索失败
    EMBEDDING_FAILED = "EMBEDDING_FAILED"                 # 嵌入失败

    # ==================== 系统相关错误 ====================
    SYSTEM_ERROR = "SYSTEM_ERROR"                         # 系统错误
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"           # 配置错误
    NETWORK_ERROR = "NETWORK_ERROR"                       # 网络错误

    # ==================== 业务逻辑错误 ====================
    INVALID_REQUEST = "INVALID_REQUEST"                   # 无效请求
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"         # 业务逻辑错误


class ErrorMessages:
    """错误消息映射"""

    MESSAGES: Dict[ErrorCode, str] = {
        # 认证相关
        ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
        ErrorCode.TOKEN_EXPIRED: "访问令牌已过期，请重新登录",
        ErrorCode.TOKEN_INVALID: "无效的访问令牌",
        ErrorCode.TOKEN_MISSING: "缺少访问令牌",
        ErrorCode.INSUFFICIENT_PERMISSIONS: "权限不足",

        # 用户相关
        ErrorCode.USER_NOT_FOUND: "用户不存在",
        ErrorCode.USER_ALREADY_EXISTS: "用户已存在",
        ErrorCode.USER_INACTIVE: "用户账户未激活",

        # 文件相关
        ErrorCode.FILE_TOO_LARGE: "文件大小超过限制",
        ErrorCode.FILE_TYPE_NOT_ALLOWED: "不支持的文件类型",
        ErrorCode.FILE_UPLOAD_FAILED: "文件上传失败",
        ErrorCode.FILE_PROCESSING_FAILED: "文件处理失败",
        ErrorCode.FILE_NOT_FOUND: "文件不存在",
        ErrorCode.NO_FILES: "请至少选择一个文件",

        # 数据库相关
        ErrorCode.DATABASE_ERROR: "数据库操作失败",
        ErrorCode.DATA_NOT_FOUND: "数据不存在",
        ErrorCode.DATA_VALIDATION_FAILED: "数据验证失败",

        # AI/向量相关
        ErrorCode.AI_SERVICE_UNAVAILABLE: "AI服务暂时不可用",
        ErrorCode.VECTOR_SEARCH_FAILED: "向量搜索失败",
        ErrorCode.EMBEDDING_FAILED: "文本嵌入失败",

        # 系统相关
        ErrorCode.SYSTEM_ERROR: "系统内部错误",
        ErrorCode.CONFIGURATION_ERROR: "系统配置错误",
        ErrorCode.NETWORK_ERROR: "网络连接错误",

        # 业务逻辑
        ErrorCode.INVALID_REQUEST: "无效的请求参数",
        ErrorCode.BUSINESS_LOGIC_ERROR: "业务逻辑错误",
    }

    @classmethod
    def get_message(cls, error_code: ErrorCode) -> str:
        """获取错误消息"""
        return cls.MESSAGES.get(error_code, "未知错误")


class VoidSystemException(Exception):
    """虚空系统统一异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误码枚举
            status_code: HTTP状态码
            details: 额外错误详情
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    @classmethod
    def from_error_code(
        cls,
        error_code: ErrorCode,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'VoidSystemException':
        """
        从错误码创建异常

        Args:
            error_code: 错误码枚举
            status_code: HTTP状态码（可选，默认根据错误类型确定）
            details: 额外错误详情

        Returns:
            VoidSystemException实例
        """
        message = ErrorMessages.get_message(error_code)

        # 根据错误码确定默认状态码
        if status_code is None:
            if error_code in [ErrorCode.INVALID_CREDENTIALS, ErrorCode.TOKEN_EXPIRED,
                            ErrorCode.TOKEN_INVALID, ErrorCode.TOKEN_MISSING]:
                status_code = 401  # Unauthorized
            elif error_code in [ErrorCode.INSUFFICIENT_PERMISSIONS]:
                status_code = 403  # Forbidden
            elif error_code in [ErrorCode.USER_NOT_FOUND, ErrorCode.FILE_NOT_FOUND,
                              ErrorCode.DATA_NOT_FOUND]:
                status_code = 404  # Not Found
            elif error_code in [ErrorCode.USER_ALREADY_EXISTS]:
                status_code = 409  # Conflict
            else:
                status_code = 400  # Bad Request

        return cls(message, error_code, status_code, details)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "error_code": self.error_code.value,
            "status_code": self.status_code,
            "details": self.details
        }


# ==================== 快捷异常创建函数 ====================

def create_auth_error(error_code: ErrorCode, details: Optional[Dict[str, Any]] = None) -> VoidSystemException:
    """创建认证相关异常"""
    return VoidSystemException.from_error_code(error_code, details=details)

def create_file_error(error_code: ErrorCode, details: Optional[Dict[str, Any]] = None) -> VoidSystemException:
    """创建文件相关异常"""
    return VoidSystemException.from_error_code(error_code, details=details)

def create_system_error(error_code: ErrorCode, details: Optional[Dict[str, Any]] = None) -> VoidSystemException:
    """创建系统相关异常"""
    return VoidSystemException.from_error_code(error_code, details=details)

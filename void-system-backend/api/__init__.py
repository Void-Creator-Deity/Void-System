"""
Void System API Package
"""

# 导出主要的API管理器实例
from .user_document_manager import document_manager
from .user_vector_manager import vector_manager
from .personalized_qa import qa_engine

__all__ = [
    'document_manager',
    'vector_manager',
    'qa_engine'
]


"""
Void System - Persona Chain (System AI Assistant)
-------------------------------------------------
系统精灵对话链，支持多轮对话和会话历史管理。
"""

from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnableLambda
from typing import Dict, Any, Optional
import uuid

# 存储会话历史（生产环境建议使用 Redis）
_store: Dict[str, ChatMessageHistory] = {}


def get_history(session_id: str) -> BaseChatMessageHistory:
    """
    获取或创建会话历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话历史对象
    """
    if session_id not in _store:
        _store[session_id] = ChatMessageHistory()
    return _store[session_id]


def load_persona_chain():
    """
    加载系统精灵对话链
    
    Returns:
        配置好的对话链 Runnable 对象
    """
    # 初始化 LLM 模型
    llm = ChatOllama(
        model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
        temperature=0.5
    )

    # 定义系统精灵的提示模板
    prompt = ChatPromptTemplate.from_template("""
    你是系统精灵「VOID AI」，语气冷静、逻辑清晰。
    你将根据用户的输入和历史对话，提供精准且有帮助的回答。
    
    用户输入：{text}
    历史对话：{history}
    
    请以系统精灵的身份，提供专业、准确的回答。
    """)

    # 构建基础链
    chain = prompt | llm

    # 包装为带历史记录的 Runnable
    base_chain = RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="text",
        history_messages_key="history",
    )
    
    def ensure_session(input_data: Dict[str, Any], config: Optional[Dict] = None) -> Any:
        """
        确保会话ID存在，如果不存在则自动生成
        
        Args:
            input_data: 输入数据
            config: 配置字典
            
        Returns:
            链的执行结果
        """
        # 从输入数据中提取 session_id（如果存在）
        if isinstance(input_data, dict) and "config" in input_data:
            input_config = input_data.get("config", {})
            if isinstance(input_config, dict):
                configurable = input_config.get("configurable", {})
                if isinstance(configurable, dict) and "session_id" in configurable:
                    session_id = configurable["session_id"]
                    if config is None:
                        config = {"configurable": {}}
                    config["configurable"]["session_id"] = session_id
                    return base_chain.invoke(input_data, config=config)
        
        # 如果没有提供 session_id，生成一个默认的
        if config is None:
            config = {"configurable": {}}
        config["configurable"]["session_id"] = f"default-{uuid.uuid4().hex[:8]}"
        
        return base_chain.invoke(input_data, config=config)
    
    # 返回包装后的 Runnable 对象
    return RunnableLambda(ensure_session)

"""
Void System - LLM Factory
--------------------------
统一的 LLM 工厂模块，支持本地 Ollama 模式和各类 API 模式。
通过 config.py 中的 LLM_PROVIDER 环境变量切换提供商。

支持的提供商 (LLM_PROVIDER):
  - ollama       : 本地 Ollama (默认)
  - openai       : OpenAI (gpt-4o, gpt-4-turbo 等)
  - deepseek     : DeepSeek API (兼容 OpenAI 协议)
  - gemini       : Google Gemini
  - openai_compat: 任意兼容 OpenAI 协议的第三方 API

嵌入模型 (EMBEDDING_PROVIDER):
  - ollama       : 本地 Ollama Embeddings (默认)
  - openai       : OpenAI text-embedding-*
  - huggingface  : HuggingFace 本地嵌入 (不需要 API Key)
"""
import logging
from typing import Any, Optional
from config import config

logger = logging.getLogger("void-system-llm-factory")


def get_chat_llm(
    temperature: float = 0.5,
    json_mode: bool = False,
) -> Any:
    """
    根据配置返回合适的 ChatLLM 实例。

    Args:
        temperature: 温度参数 (创意度)
        json_mode:   是否强制 JSON 输出 (仅 Ollama 支持 format='json')

    Returns:
        LangChain ChatModel 实例
    """
    provider = config.LLM_PROVIDER.lower()
    logger.info(f"🤖 初始化 LLM 提供商: {provider} | 模型: {config.CHAT_MODEL}")

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = {
            "model": config.CHAT_MODEL,
            "base_url": config.OLLAMA_BASE_URL,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["format"] = "json"
        return ChatOllama(**kwargs)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        _require_key("OPENAI_API_KEY")
        return ChatOpenAI(
            model=config.CHAT_MODEL,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
        )

    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        _require_key("OPENAI_API_KEY", hint="DeepSeek 使用 OPENAI_API_KEY 存放 DeepSeek API Key")
        return ChatOpenAI(
            model=config.CHAT_MODEL or "deepseek-chat",
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL or "https://api.deepseek.com/v1",
        )

    elif provider in ("openai_compat", "compatible"):
        # 支持 moonshot, qwen, yi, groq 等任意 OpenAI 兼容的第三方 API
        from langchain_openai import ChatOpenAI
        _require_key("OPENAI_API_KEY", hint="请设置 OPENAI_API_KEY 为对应平台的 API Key")
        _require_key("OPENAI_BASE_URL", hint="请设置 OPENAI_BASE_URL 为对应平台的 Base URL")
        return ChatOpenAI(
            model=config.CHAT_MODEL,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        _require_key("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=config.CHAT_MODEL or "gemini-1.5-flash",
            temperature=temperature,
            google_api_key=config.GOOGLE_API_KEY,
        )

    else:
        logger.warning(f"⚠️ 未知的 LLM_PROVIDER: '{provider}'，回退到 Ollama")
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=config.CHAT_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=temperature,
        )


def get_embeddings() -> Any:
    """
    根据配置返回合适的 Embeddings 实例。

    Returns:
        LangChain Embeddings 实例
    """
    provider = config.EMBEDDING_PROVIDER.lower()
    logger.info(f"🔢 初始化 Embeddings 提供商: {provider} | 模型: {config.EMBEDDING_MODEL}")

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=config.EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        _require_key("OPENAI_API_KEY")
        return OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL or "text-embedding-3-small",
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL or None,
        )

    elif provider == "huggingface":
        raise EnvironmentError(
            "EMBEDDING_PROVIDER=huggingface 已在当前项目中移除。"
            "请改用 EMBEDDING_PROVIDER=ollama 或 EMBEDDING_PROVIDER=openai。"
        )

    else:
        logger.warning(f"⚠️ 未知的 EMBEDDING_PROVIDER: '{provider}'，回退到 Ollama")
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=config.EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )


def _require_key(key_name: str, hint: str = "") -> None:
    """检查必要的 API Key 是否已配置"""
    value = getattr(config, key_name, None)
    if not value:
        msg = f"❌ 缺少必要的 API Key: {key_name}"
        if hint:
            msg += f" ({hint})"
        msg += f"。请在 .env 文件中设置 {key_name}=your_key"
        raise EnvironmentError(msg)

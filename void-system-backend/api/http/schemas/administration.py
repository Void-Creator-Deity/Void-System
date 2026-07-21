"""HTTP schemas for administration settings."""

from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class AIConfigUpdateRequest(BaseModel):
    llm_provider: Optional[str] = Field(default=None, max_length=40)
    embedding_provider: Optional[str] = Field(default=None, max_length=40)
    ollama_base_url: Optional[str] = Field(default=None, max_length=500)
    chat_model: Optional[str] = Field(default=None, max_length=300)
    embedding_model: Optional[str] = Field(default=None, max_length=300)
    openai_base_url: Optional[str] = Field(default=None, max_length=500)
    openai_api_key: Optional[str] = Field(default=None, max_length=1000)
    google_api_key: Optional[str] = Field(default=None, max_length=1000)
    extra_env: Optional[Dict[str, str]] = None
    persist_to_env: bool = True
    apply_runtime: bool = True

    @field_validator("extra_env")
    @classmethod
    def limit_advanced_overrides(cls, value: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        if value is not None and len(value) > 20:
            raise ValueError("高级配置一次最多修改 20 项")
        return value


class AIConfigModelListRequest(BaseModel):
    llm_provider: Optional[str] = Field(default=None, max_length=40)
    ollama_base_url: Optional[str] = Field(default=None, max_length=500)
    openai_base_url: Optional[str] = Field(default=None, max_length=500)
    openai_api_key: Optional[str] = Field(default=None, max_length=1000)
    google_api_key: Optional[str] = Field(default=None, max_length=1000)


class AIConfigTestRequest(BaseModel):
    llm_provider: Optional[str] = Field(default=None, max_length=40)
    ollama_base_url: Optional[str] = Field(default=None, max_length=500)
    chat_model: Optional[str] = Field(default=None, max_length=300)
    openai_base_url: Optional[str] = Field(default=None, max_length=500)
    openai_api_key: Optional[str] = Field(default=None, max_length=1000)
    google_api_key: Optional[str] = Field(default=None, max_length=1000)

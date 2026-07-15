"""HTTP schemas for conversation workflows."""
from typing import Optional

from pydantic import BaseModel, Field


class ChatGroupCreate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=50)


class ChatGroupUpdate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=50)


class ChatSessionCreate(BaseModel):
    group_id: str = Field(..., min_length=1, max_length=80)
    session_name: str = Field(..., min_length=1, max_length=100)
    session_id: Optional[str] = Field(None, min_length=1, max_length=80)


class ChatSessionUpdate(BaseModel):
    session_name: Optional[str] = Field(None, min_length=1, max_length=100)
    group_id: Optional[str] = Field(None, min_length=1, max_length=80)


class ChatMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=200000)
    tokens: int = Field(0, ge=0)
    reply_to_id: Optional[str] = Field(None, min_length=1, max_length=80)

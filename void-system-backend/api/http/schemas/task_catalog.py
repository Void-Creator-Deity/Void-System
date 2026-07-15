"""Transport schemas for the legacy task catalog endpoints."""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TaskCategoryCreate(BaseModel):
    """A user-defined task grouping."""

    category_name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field("", max_length=200)
    icon: Optional[str] = "📚"
    color: Optional[str] = "#3B82F6"

    @field_validator("category_name")
    @classmethod
    def normalize_category_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("任务分类名称不能为空")
        return normalized


class TaskCategoryUpdate(BaseModel):
    """Partial update for a task grouping."""

    category_name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = None
    color: Optional[str] = None

    @field_validator("category_name")
    @classmethod
    def normalize_category_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("任务分类名称不能为空")
        return normalized

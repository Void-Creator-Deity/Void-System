"""Request contracts for the user-facing Task Workspace API."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    """Create a standalone task in the current user's workspace."""

    task_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field("", max_length=500)
    related_attrs: Optional[Dict[str, Any]] = None
    estimated_time: Optional[int] = Field(30, ge=1, le=480)
    reward_coins: Optional[int] = Field(10, ge=0, le=1000)
    priority: Optional[str] = Field("medium", pattern="^(easy|medium|hard)$")
    attribute_points: Optional[int] = Field(0, ge=0, le=100)
    category_id: Optional[str] = None
    chain_id: Optional[str] = None
    chain_order: Optional[int] = 0
    completion_type: Optional[str] = "simple"
    completion_criteria: Optional[Dict[str, Any]] = None
    prerequisites: Optional[List[str]] = None
    task_type: Optional[str] = "main"
    is_optional: Optional[bool] = False
    is_daily: Optional[bool] = False

    @field_validator("category_id", "chain_id", mode="before")
    @classmethod
    def blank_id_to_none(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        return str(value)

    @field_validator("prerequisites", mode="before")
    @classmethod
    def prerequisites_to_str_list(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, list):
            return [str(item) for item in value]
        return value

    @field_validator("is_optional", "is_daily", mode="before")
    @classmethod
    def coerce_bool_flags(cls, value: Any) -> Any:
        if value in (0, "0", "false", False):
            return False
        if value in (1, "1", "true", True):
            return True
        return value

    @field_validator("related_attrs")
    @classmethod
    def validate_related_attrs(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if value is not None:
            for attribute_id, weight in value.items():
                if not isinstance(weight, (int, float)):
                    raise ValueError(f"属性 {attribute_id} 的值必须是数字")
        return value


class TaskStepCreate(BaseModel):
    """A user-provided step for a task workflow."""

    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    related_attrs: Optional[Dict[str, Any]] = None
    estimated_time: Optional[int] = Field(30, ge=1, le=480)
    reward_coins: Optional[int] = Field(20, ge=0, le=1000)
    priority: Optional[str] = Field("medium", pattern="^(easy|medium|hard)$")
    attribute_points: Optional[int] = Field(5, ge=0, le=100)
    completion_type: Optional[str] = "ai_eval"
    completion_criteria: Optional[Dict[str, Any]] = None
    task_type: Optional[str] = "main"
    is_optional: Optional[bool] = False


class TaskChainCreate(BaseModel):
    """Create a task workflow from explicit steps or a goal."""

    chain_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field("", max_length=500)
    target_goal: Optional[str] = Field(None, min_length=1, max_length=1000)
    steps: Optional[List[TaskStepCreate]] = Field(None, max_length=50)


class TaskProgressUpdate(BaseModel):
    """Set the measurable progress for an existing task."""

    progress: int = Field(..., ge=0, le=100)

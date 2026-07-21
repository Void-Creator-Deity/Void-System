"""HTTP request schemas for Trigger-to-Run automation."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from api.http.schemas.task_execution import RunStepCreate


class TriggerRunTemplate(BaseModel):
    title: Optional[str] = Field(None, max_length=160)
    objective: str = Field("", max_length=2000)
    mode: Literal["manual", "assisted"] = "manual"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    steps: Optional[List[RunStepCreate]] = Field(None, max_length=100)


class TriggerCreate(BaseModel):
    goal_id: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=160)
    trigger_type: Literal["schedule", "event"]
    configuration: Dict[str, Any] = Field(default_factory=dict)
    run_template: TriggerRunTemplate


class TriggerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=160)
    configuration: Optional[Dict[str, Any]] = None
    run_template: Optional[TriggerRunTemplate] = None


class TriggerFireRequest(BaseModel):
    source_key: str = Field(..., min_length=1, max_length=200)
    payload: Dict[str, Any] = Field(default_factory=dict)

"""Transport schemas for Planning Engine routes."""
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class AdvisorRequest(BaseModel):
    topic: str = Field(default="", max_length=1000)
    force_mode: Literal["auto", "single_task", "workflow_chain"] = "auto"
    advisor_prefs: Dict[str, Any] = Field(default_factory=dict)


class RunPlanRequest(BaseModel):
    """Generate a reviewable Goal and Run specification."""

    topic: str = Field(..., min_length=1, max_length=1000)
    execution_mode: Literal["manual", "assisted", "agent"] = "assisted"
    max_steps: int = Field(8, ge=1, le=20)
    advisor_prefs: Dict[str, Any] = Field(default_factory=dict)

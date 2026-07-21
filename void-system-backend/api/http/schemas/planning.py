"""Transport schemas for Planning Engine routes."""
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class RunPlanRequest(BaseModel):
    """Generate a reviewable Goal and Run specification."""

    topic: str = Field(..., min_length=1, max_length=1000)
    execution_mode: Literal["manual", "assisted"] = "assisted"
    max_steps: int = Field(8, ge=1, le=20)
    advisor_prefs: Dict[str, Any] = Field(default_factory=dict)


class PlanDraftUpdateRequest(BaseModel):
    """Save a complete editable Plan Draft using optimistic concurrency."""

    payload: Dict[str, Any]
    expected_version: int = Field(..., ge=1)


class PlanDraftPublishRequest(BaseModel):
    """Publish a stored Plan Draft with a stable retry key."""

    idempotency_key: str = Field(..., min_length=1, max_length=200)

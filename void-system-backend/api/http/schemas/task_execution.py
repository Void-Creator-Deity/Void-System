"""HTTP request schemas for Goal and Run execution."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field("", max_length=2000)
    desired_outcome: str = Field("", max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    description: Optional[str] = Field(None, max_length=2000)
    desired_outcome: Optional[str] = Field(None, max_length=2000)
    priority: Optional[Literal["low", "medium", "high"]] = None
    status: Optional[Literal["active", "completed", "archived"]] = None
    metadata: Optional[Dict[str, Any]] = None


class RunStepCreate(BaseModel):
    client_key: Optional[str] = Field(None, max_length=100)
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field("", max_length=2000)
    kind: Literal["manual", "agent", "tool", "review"] = "manual"
    depends_on: List[str] = Field(default_factory=list, max_length=100)
    parallel_group: Optional[str] = Field(None, max_length=100)
    max_attempts: int = Field(1, ge=1, le=10)
    requires_approval: bool = False
    completion_criteria: Dict[str, Any] = Field(default_factory=dict)
    input_data: Dict[str, Any] = Field(default_factory=dict)


class RunCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=160)
    objective: str = Field("", max_length=2000)
    mode: Literal["manual", "assisted", "agent"] = "manual"
    idempotency_key: Optional[str] = Field(None, max_length=200)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    steps: Optional[List[RunStepCreate]] = Field(None, max_length=100)


class RunCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)


class RunLeaseClaimRequest(BaseModel):
    worker_id: str = Field(..., min_length=1, max_length=200)
    lease_seconds: int = Field(60, ge=10, le=3600)


class RunLeaseHeartbeatRequest(BaseModel):
    lease_token: str = Field(..., min_length=1, max_length=200)
    lease_seconds: int = Field(60, ge=10, le=3600)
    checkpoint_data: Optional[Dict[str, Any]] = None


class RunLeaseReleaseRequest(BaseModel):
    lease_token: str = Field(..., min_length=1, max_length=200)
    checkpoint_data: Optional[Dict[str, Any]] = None


class ArtifactCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    kind: str = Field("result", min_length=1, max_length=60)
    uri: Optional[str] = Field(None, max_length=2000)
    content_type: Optional[str] = Field(None, max_length=200)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepCompleteRequest(BaseModel):
    output_data: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[ArtifactCreate] = Field(default_factory=list, max_length=50)


class StepFailRequest(BaseModel):
    error_summary: str = Field(..., min_length=1, max_length=2000)


class ApprovalRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=1000)
    details: Dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = Field(None, max_length=2000)


class ActionStartRequest(BaseModel):
    action_type: Optional[str] = Field(None, max_length=60)
    tool_name: Optional[str] = Field(None, max_length=200)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(None, max_length=200)


class ActionCompleteRequest(BaseModel):
    status: Literal["completed", "failed", "cancelled"]
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_summary: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def require_failure_reason(self) -> "ActionCompleteRequest":
        if self.status == "failed" and not self.error_summary:
            raise ValueError("error_summary is required when an action fails")
        return self

"""HTTP request schemas for the system companion and personal context."""
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class CompanionSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    tone: Optional[Literal["calm", "warm", "direct"]] = None
    initiative: Optional[Literal["quiet", "balanced", "proactive"]] = None
    permissions: Optional[Dict[str, bool]] = None


class MemoryCreate(BaseModel):
    memory_type: Literal["fact", "preference", "episode", "inference"] = "fact"
    title: str = Field(..., min_length=1, max_length=160)
    content: str = Field(..., min_length=1, max_length=4000)
    source_type: str = Field("manual", min_length=1, max_length=60)
    source_ref: Optional[str] = Field(None, max_length=500)
    confidence: float = Field(1.0, ge=0, le=1)
    use_in_context: bool = True
    contribute_to_profile: bool = False
    expires_at: Optional[str] = Field(None, max_length=80)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    memory_type: Optional[Literal["fact", "preference", "episode", "inference"]] = None
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    source_type: Optional[str] = Field(None, min_length=1, max_length=60)
    source_ref: Optional[str] = Field(None, max_length=500)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    use_in_context: Optional[bool] = None
    contribute_to_profile: Optional[bool] = None
    status: Optional[Literal["active", "archived"]] = None
    expires_at: Optional[str] = Field(None, max_length=80)
    metadata: Optional[Dict[str, Any]] = None


class MemoryReview(BaseModel):
    decision: Literal["confirmed", "corrected", "rejected"]
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    memory_type: Optional[Literal["fact", "preference", "episode", "inference"]] = None
    use_in_context: Optional[bool] = None
    reason: str = Field("", max_length=500)


class ProfileObservationCreate(BaseModel):
    kind: Literal["favorite", "feedback", "task", "conversation", "import", "manual"] = "manual"
    summary: str = Field(..., min_length=1, max_length=500)
    source_type: str = Field("manual", min_length=1, max_length=60)
    source_ref: Optional[str] = Field(None, max_length=500)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(1.0, ge=0, le=1)
    observed_at: Optional[str] = None
    sensitivity: Literal["personal", "private", "sensitive"] = "private"
    status: Literal["active", "archived"] = "active"


class ProfileClaimCreate(BaseModel):
    domain: Literal[
        "basic", "interests", "working_style", "communication", "values", "current_phase"
    ]
    profile_key: str = Field(..., min_length=1, max_length=160)
    value: Any
    summary: str = Field(..., min_length=1, max_length=240)
    rationale: str = Field("", max_length=1000)
    confidence: float = Field(0.5, ge=0, le=1)
    review_status: Literal["pending", "confirmed", "rejected", "corrected"] = "pending"
    evidence_refs: list[Dict[str, Any]] = Field(default_factory=list)
    first_observed_at: Optional[str] = None
    last_observed_at: Optional[str] = None
    status: Literal["active", "archived"] = "active"


class ProfileClaimReview(BaseModel):
    decision: Literal["pending", "confirmed", "rejected", "corrected"]
    value: Any = None
    reason: str = Field("", max_length=500)


class ProfileSuggestionReview(BaseModel):
    decision: Literal["confirmed", "rejected", "corrected"]
    value: Any = None
    reason: str = Field("", max_length=500)

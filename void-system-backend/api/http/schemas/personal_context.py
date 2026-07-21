"""HTTP request schemas for the system companion and personal context."""
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class CompanionSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    tone: Optional[Literal["calm", "warm", "direct"]] = None
    initiative: Optional[Literal["quiet", "balanced", "proactive"]] = None
    persona: Optional[Dict[str, str]] = None
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


class ProfileHypothesisReview(BaseModel):
    """A user's explicit decision about one AI-organized understanding."""

    decision: Literal["confirmed", "rejected", "corrected"]
    value: Any = None
    reason: str = Field("", max_length=500)


class ProfileHypothesisInferenceRequest(BaseModel):
    """Bounded request to organize safe profile signals into reviewable hypotheses."""

    max_signals: int = Field(24, ge=3, le=48)
    max_hypotheses: int = Field(4, ge=1, le=6)

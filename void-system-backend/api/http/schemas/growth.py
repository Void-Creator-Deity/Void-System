"""Request schemas for the user's growth profile and reward balance."""
from typing import Optional

from pydantic import BaseModel, Field


class AttributeCreate(BaseModel):
    """Create a user-defined growth attribute."""

    attr_name: str = Field(..., min_length=1, max_length=50)
    max_value: int = Field(default=100, ge=1, le=999)
    description: Optional[str] = Field("", max_length=200)
    icon: Optional[str] = "📊"


class AttributeUpdate(BaseModel):
    """Update one or more editable fields of a growth attribute."""

    attr_name: Optional[str] = Field(None, min_length=1, max_length=50)
    attr_value: Optional[int] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=200)
    max_value: Optional[int] = Field(None, ge=1, le=999)

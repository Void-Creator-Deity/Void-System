"""Transport schemas for Reward Marketplace endpoints."""

from pydantic import BaseModel, Field


class PurchaseRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=10)

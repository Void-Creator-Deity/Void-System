"""Transport schemas for Task Workflow routes."""
from typing import List, Optional

from pydantic import BaseModel, Field


class AIEvaluateRequest(BaseModel):
    submission: str = Field(..., min_length=1)
    submission_type: str = "text"
    media_urls: Optional[List[str]] = None

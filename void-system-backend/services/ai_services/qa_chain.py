"""Retired legacy QA chain.

User knowledge queries must use the authenticated KnowledgeEngine route instead
of constructing a second process-wide Chroma and LLM pipeline.
"""
from __future__ import annotations

from typing import Any


class LegacyKnowledgePipelineRetired(RuntimeError):
    """Raised when code attempts to use the removed global QA pipeline."""


def load_qa_chain(*_: Any, **__: Any) -> Any:
    """Reject retired global QA construction with a clear migration path."""
    raise LegacyKnowledgePipelineRetired(
        "The legacy QA chain was retired. Use the authenticated /api/user/qa/ask workflow."
    )

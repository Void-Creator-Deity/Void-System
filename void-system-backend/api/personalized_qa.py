"""Retired compatibility module for the old personalized QA singleton.

The product-facing knowledge workflow is composed by modules.knowledge.service
and served through authenticated HTTP routes.
"""
from __future__ import annotations


class LegacyPersonalizedQAEngineRetired(RuntimeError):
    """Raised when callers request the removed global personalized QA engine."""


def get_legacy_qa_engine() -> None:
    """Fail explicitly instead of initializing an unscoped vector/model singleton."""
    raise LegacyPersonalizedQAEngineRetired(
        "The global personalized QA engine was retired. Use modules.knowledge.service resources."
    )

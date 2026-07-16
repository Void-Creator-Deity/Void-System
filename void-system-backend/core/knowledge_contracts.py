"""
Portable knowledge contracts.

These dataclasses and protocols form the seam between product use cases and the
current retrieval implementation. The rest of the app should depend on these
interfaces instead of Chroma, LangChain chains, or document-parser details.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence


class KnowledgeScope(str, Enum):
    """Where a knowledge item is visible."""

    SYSTEM = "system"
    USER = "user"
    SESSION = "session"


@dataclass(frozen=True)
class IngestSource:
    """Raw document bytes plus product-level ownership metadata."""

    owner_id: str
    file_name: str
    content: bytes
    scope: KnowledgeScope = KnowledgeScope.USER
    title: Optional[str] = None
    tags: Sequence[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    """Normalized text ready for indexing."""

    document_id: str
    owner_id: str
    title: str
    text: str
    file_name: str
    file_type: str
    scope: KnowledgeScope
    tags: Sequence[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeChunk:
    """A retrievable unit with enough metadata to cite and filter."""

    chunk_id: str
    document_id: str
    owner_id: str
    text: str
    scope: KnowledgeScope
    score: Optional[float] = None
    title: Optional[str] = None
    file_name: Optional[str] = None
    chunk_index: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeQuery:
    """Search request used by all knowledge-backed features."""

    question: str
    owner_id: Optional[str] = None
    scopes: Sequence[KnowledgeScope] = field(default_factory=lambda: (KnowledgeScope.USER, KnowledgeScope.SYSTEM))
    document_ids: Optional[Sequence[str]] = None
    top_k: int = 6
    mode: str = "hybrid"
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeAnswer:
    """Answer plus traceable evidence."""

    answer: str
    citations: Sequence[KnowledgeChunk] = field(default_factory=list)
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceAssessment:
    """Implementation-neutral decision about whether retrieved text can support an answer."""

    answerable: bool
    reason: str
    candidate_count: int
    usable_count: int
    source_count: int
    top_relevance: float
    mean_relevance: float
    evidence: Sequence[KnowledgeChunk] = field(default_factory=list)

    def as_metadata(self) -> Dict[str, Any]:
        """Return stable, serializable quality metadata for API consumers and traces."""
        return {
            "answerable": self.answerable,
            "reason": self.reason,
            "candidate_count": self.candidate_count,
            "usable_count": self.usable_count,
            "source_count": self.source_count,
            "top_relevance": round(self.top_relevance, 4),
            "mean_relevance": round(self.mean_relevance, 4),
        }


class KnowledgeIndex(Protocol):
    """Adapter interface for vector, keyword, graph, or hybrid indexes."""

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        """Return candidate chunks for the query."""

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        """Delete indexed chunks for one document."""


class GroundedGenerator(Protocol):
    """Model seam that generates text from already selected evidence."""

    async def generate(self, question: str, evidence: str) -> str:
        """Generate a grounded answer without performing retrieval."""


class KnowledgeResponder(Protocol):
    """Adapter interface for answer synthesis over retrieved chunks."""

    async def answer(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> KnowledgeAnswer:
        """Create an answer grounded in chunks."""


class KnowledgeIngestor(Protocol):
    """Adapter interface for document ingestion pipelines."""

    async def ingest(self, source: IngestSource) -> Dict[str, Any]:
        """Store, parse, and index a source document."""


class KnowledgeTraceRecorder(Protocol):
    """Optional audit seam for user-visible knowledge activity."""

    def record_retrieval(
        self,
        *,
        owner_id: str,
        question: str,
        mode: str,
        candidate_count: int,
        ranked_count: int,
        citations: Sequence[Dict[str, Any]],
    ) -> str:
        """Persist an implementation-neutral retrieval trace."""


class KnowledgeUseEventRecorder(Protocol):
    """Optional privacy-minimized activity seam for aggregate behavior insights."""

    def record_knowledge_use(
        self,
        *,
        owner_id: str,
        mode: str,
        candidate_count: int,
        ranked_count: int,
        source_count: int,
        citation_count: int,
        answerable: bool,
    ) -> str:
        """Persist aggregate retrieval outcome without question or document content."""


class Reranker(Protocol):
    """Optional ranking adapter, intentionally separate from retrieval."""

    def rerank(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> Sequence[KnowledgeChunk]:
        """Return chunks in final evidence order."""


class EvidenceQualityPolicy(Protocol):
    """Decide whether ranked chunks are sufficient evidence for an answer."""

    def assess(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> EvidenceAssessment:
        """Return the selected, answerable evidence and an explanation of the decision."""


class NullReranker:
    """Default adapter used until a real reranker is configured."""

    def rerank(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> Sequence[KnowledgeChunk]:
        return list(chunks)

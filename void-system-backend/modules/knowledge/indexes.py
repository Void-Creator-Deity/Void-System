"""Scope-aware retrieval indexes over the unified Chroma knowledge store."""
from __future__ import annotations

from typing import Callable, Dict, Mapping, Sequence

from adapters.chroma.knowledge_store import ChromaKnowledgeStore
from core.knowledge_contracts import KnowledgeChunk, KnowledgeIndex, KnowledgeQuery, KnowledgeScope

CatalogResolver = Callable[[KnowledgeQuery, KnowledgeScope], Mapping[str, Mapping[str, object]]]


class ScopedSemanticIndex(KnowledgeIndex):
    """Semantic recall for every requested persistent scope through one store.

    Inputs: a scope catalog resolver and ChromaKnowledgeStore. Output: candidate
    chunks whose document ids are eligible in the application catalog. Called by
    the hybrid Knowledge Engine. It never decides document visibility itself.
    """

    def __init__(self, store: ChromaKnowledgeStore, catalog: CatalogResolver) -> None:
        self._store = store
        self._catalog = catalog

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        results: list[KnowledgeChunk] = []
        for scope in query.scopes:
            if scope not in {KnowledgeScope.USER, KnowledgeScope.SYSTEM}:
                continue
            results.extend(self._store.semantic_search(
                query=query,
                scope=scope,
                catalog=self._catalog(query, scope),
            ))
        return results[: query.top_k]

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        if scope not in {KnowledgeScope.USER, KnowledgeScope.SYSTEM}:
            return False
        return self._store.delete_document(
            scope=scope,
            owner_id=owner_id if scope == KnowledgeScope.USER else "system",
            document_id=document_id,
        )


class ScopedLexicalIndex(KnowledgeIndex):
    """Lexical recall for every requested persistent scope through one store."""

    def __init__(self, store: ChromaKnowledgeStore, catalog: CatalogResolver) -> None:
        self._store = store
        self._catalog = catalog

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        results: list[KnowledgeChunk] = []
        for scope in query.scopes:
            if scope not in {KnowledgeScope.USER, KnowledgeScope.SYSTEM}:
                continue
            results.extend(self._store.lexical_search(
                query=query,
                scope=scope,
                catalog=self._catalog(query, scope),
            ))
        return results[: query.top_k]

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        return False

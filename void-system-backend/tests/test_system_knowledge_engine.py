"""Regression tests for shared retrieval through the unified store indexes."""
from __future__ import annotations

import unittest

from core.knowledge_contracts import KnowledgeChunk, KnowledgeQuery, KnowledgeScope
from modules.knowledge.indexes import ScopedLexicalIndex, ScopedSemanticIndex


class FakeStore:
    def __init__(self) -> None:
        self.semantic_calls = []
        self.lexical_calls = []

    def semantic_search(self, *, query, scope, catalog):
        self.semantic_calls.append((query, scope, catalog))
        return [KnowledgeChunk("chunk-1", "system-1", "system", "Incident response guide", scope, 0.82, "Operations handbook", "handbook.md", 0)]

    def lexical_search(self, *, query, scope, catalog):
        self.lexical_calls.append((query, scope, catalog))
        return [KnowledgeChunk("chunk-1", "system-1", "system", "Incident response guide", scope, 2.0, "Operations handbook", "handbook.md", 0)]


class SystemKnowledgeIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = FakeStore()

        def catalog(query, scope):
            self.catalog_query = (query, scope)
            if scope != KnowledgeScope.SYSTEM:
                return {}
            return {"system-1": {"title": "Operations handbook", "file_name": "handbook.md", "tags": ["ops"]}}

        self.catalog = catalog

    def test_semantic_index_reads_shared_scope_from_the_unified_store(self) -> None:
        index = ScopedSemanticIndex(self.store, self.catalog)
        query = KnowledgeQuery(question="incident response", scopes=(KnowledgeScope.SYSTEM,))
        result = index.search(query)
        self.assertEqual([item.document_id for item in result], ["system-1"])
        self.assertEqual(self.store.semantic_calls[0][1], KnowledgeScope.SYSTEM)
        self.assertIn("system-1", self.store.semantic_calls[0][2])

    def test_lexical_index_passes_only_the_requested_personal_scope_to_the_store(self) -> None:
        index = ScopedLexicalIndex(self.store, self.catalog)
        result = index.search(KnowledgeQuery(owner_id="u1", question="incident", scopes=(KnowledgeScope.USER,)))
        self.assertEqual(len(result), 1)
        self.assertEqual(self.store.lexical_calls[0][1], KnowledgeScope.USER)
        self.assertEqual(self.catalog_query[1], KnowledgeScope.USER)


if __name__ == "__main__":
    unittest.main()

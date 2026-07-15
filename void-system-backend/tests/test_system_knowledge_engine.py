"""Regression tests for system knowledge retrieval through portable contracts."""
from __future__ import annotations

import unittest

from adapters.legacy.knowledge_adapters import LegacySystemLexicalIndex, LegacySystemVectorIndex
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope


class _Document:
    def __init__(self, text, metadata):
        self.page_content = text
        self.metadata = metadata


class _VectorStore:
    def __init__(self):
        self.documents = [
            _Document("The handbook explains incident response.", {"doc_id": "system-1", "chunk_index": 0}),
            _Document("Hidden content", {"doc_id": "inactive", "chunk_index": 0}),
        ]

    def similarity_search_with_relevance_scores(self, question, k):
        del question, k
        return [(document, 0.82) for document in self.documents]

    def get(self, **kwargs):
        del kwargs
        return {
            "documents": [document.page_content for document in self.documents],
            "metadatas": [document.metadata for document in self.documents],
        }


class _Catalog:
    def list_system_rag_documents(self, tags=None):
        rows = [
            {"id": "system-1", "title": "Operations handbook", "file_name": "handbook.md", "tags": ["ops"], "description": "Runbooks"},
        ]
        if tags:
            return [row for row in rows if all(tag in row["tags"] for tag in tags)]
        return rows


class _Manager:
    def __init__(self):
        self.vector_db = _VectorStore()
        self.db = _Catalog()


class SystemKnowledgeIndexTests(unittest.TestCase):
    def test_semantic_index_only_returns_active_system_catalog_documents(self):
        results = LegacySystemVectorIndex(_Manager()).search(
            KnowledgeQuery(question="incident response", scopes=(KnowledgeScope.SYSTEM,), top_k=5)
        )

        self.assertEqual(1, len(results))
        self.assertEqual("system-1", results[0].document_id)
        self.assertEqual(KnowledgeScope.SYSTEM, results[0].scope)
        self.assertEqual("Operations handbook", results[0].title)

    def test_lexical_index_honors_scope_and_tag_filters(self):
        index = LegacySystemLexicalIndex(_Manager())
        no_scope_results = index.search(
            KnowledgeQuery(question="incident", scopes=(KnowledgeScope.USER,), top_k=5)
        )
        filtered_results = index.search(
            KnowledgeQuery(
                question="incident",
                scopes=(KnowledgeScope.SYSTEM,),
                top_k=5,
                filters={"tags": ["ops"]},
            )
        )

        self.assertEqual([], no_scope_results)
        self.assertEqual(1, len(filtered_results))
        self.assertEqual(["ops"], filtered_results[0].metadata["tags"])


if __name__ == "__main__":
    unittest.main()

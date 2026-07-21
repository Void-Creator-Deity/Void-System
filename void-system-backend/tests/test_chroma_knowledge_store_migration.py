"""Integration coverage for the one-way shared Chroma migration."""
from __future__ import annotations

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chromadb
from chromadb.api.client import SharedSystemClient

from adapters.chroma.knowledge_store import (
    ChromaKnowledgeStore,
    LEGACY_SYSTEM_COLLECTION,
    SYSTEM_COLLECTION,
)
from core.runtime_settings import RuntimeSettings


class ChromaKnowledgeStoreMigrationTests(unittest.TestCase):
    def test_migrates_catalog_owned_chunks_and_removes_orphans_idempotently(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        client = None
        store = None
        source = None
        target = None
        try:
            settings = RuntimeSettings(BASE_DIR=Path(temporary_directory.name), CHROMA_PERSIST_DIR="knowledge")
            chroma_path = settings.get_chroma_path()
            client = chromadb.PersistentClient(path=str(chroma_path))
            source = client.get_or_create_collection(LEGACY_SYSTEM_COLLECTION)
            source.add(
                ids=["owned-chunk", "orphan-chunk"],
                documents=["The release runbook", "Untracked old content"],
                metadatas=[{"doc_id": "doc-1", "title": "Old title"}, {"legacy": "true"}],
                embeddings=[[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]],
            )
            catalog = {"doc-1": {"title": "Release runbook", "file_name": "release.md", "tags": ["ops"]}}
            with patch("adapters.chroma.knowledge_store.get_embeddings", return_value=object()):
                store = ChromaKnowledgeStore(settings)
                result = store.migrate_legacy_shared_collection(catalog)
                repeated = store.migrate_legacy_shared_collection(catalog)

            self.assertTrue(result["migrated"])
            self.assertEqual(result["copied_chunks"], 1)
            self.assertEqual(result["removed_orphan_chunks"], 1)
            self.assertEqual(repeated["reason"], "legacy_collection_absent")
            self.assertNotIn(LEGACY_SYSTEM_COLLECTION, {item.name for item in client.list_collections()})
            target = client.get_collection(SYSTEM_COLLECTION)
            migrated = target.get(include=["documents", "metadatas", "embeddings"])
            self.assertEqual(migrated["ids"], ["owned-chunk"])
            self.assertEqual(migrated["documents"], ["The release runbook"])
            self.assertEqual(migrated["metadatas"][0]["doc_id"], "doc-1")
            self.assertEqual(migrated["metadatas"][0]["scope"], "system")
            self.assertEqual(migrated["metadatas"][0]["title"], "Release runbook")
            for actual, expected in zip(migrated["embeddings"][0], [0.1, 0.2, 0.3]):
                self.assertAlmostEqual(float(actual), expected, places=6)
        finally:
            if store is not None:
                store.close()
            if client is not None:
                client.close()
            source = None
            target = None
            store = None
            client = None
            SharedSystemClient.clear_system_cache()
            gc.collect()
            temporary_directory.cleanup()


if __name__ == "__main__":
    unittest.main()

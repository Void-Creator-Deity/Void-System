"""Regression tests for worker-owned personal image knowledge processing."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.knowledge_contracts import KnowledgeScope
from core.runtime_settings import RuntimeSettings
from modules.knowledge.personal_documents import PersonalKnowledgeDocumentManager


class _ImageDatabase:
    def __init__(self, document) -> None:
        self.document = document
        self.status_updates = []

    def get_user_document(self, user_id, doc_id):
        return self.document

    def update_user_document_status(self, doc_id, status, **kwargs):
        self.status_updates.append((status, kwargs))
        self.document.update({"parse_status": status, **kwargs})
        return True


class _ImageStore:
    def __init__(self) -> None:
        self.calls = []

    def index_text(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(chunk_ids=["chunk-1"], collection="user_member-1_docs")

    def delete_document(self, **kwargs):
        return True


class ImageKnowledgeIngestionTests(unittest.TestCase):
    def test_worker_indexes_grounded_vision_description(self) -> None:
        async def describe_image(file_data: bytes, file_name: str) -> str:
            self.assertEqual(file_data, b"image-bytes")
            self.assertEqual(file_name, "board.png")
            return "The board lists a release goal, two milestones, and a blocked deployment."

        with tempfile.TemporaryDirectory() as temporary_directory:
            settings = RuntimeSettings(BASE_DIR=Path(temporary_directory))
            source_path = Path(temporary_directory) / "board.bin"
            database = _ImageDatabase({"doc_id": "image-1", "title": "Project board", "original_name": "board.png", "storage_path": str(source_path), "parse_status": "processing"})
            store = _ImageStore()
            manager = PersonalKnowledgeDocumentManager(storage_path=temporary_directory, database=database, store=store, settings=settings, image_describer=describe_image)
            source_path.write_bytes(manager._cipher.encrypt(b"image-bytes"))
            database.document["encryption_version"] = manager._cipher.VERSION
            parser = SimpleNamespace(get_supported_types=lambda: ["png"], parse_file=lambda *_: {"success": True, "content": "", "requires_vision_enrichment": True})
            with patch("modules.knowledge.personal_documents.document_parser", parser):
                result = asyncio.run(manager.process_stored_document("member-1", "image-1"))

        self.assertTrue(result["success"])
        self.assertEqual(result["chunk_count"], 1)
        self.assertEqual(store.calls[0]["scope"], KnowledgeScope.USER)
        self.assertEqual(store.calls[0]["text"], "The board lists a release goal, two milestones, and a blocked deployment.")
        self.assertEqual(store.calls[0]["metadata"]["file_type"], "png")
        self.assertEqual(database.document["parse_status"], "completed")

    def test_worker_does_not_index_when_vision_description_fails(self) -> None:
        async def failing_describer(file_data: bytes, file_name: str) -> str:
            raise RuntimeError("vision service unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            settings = RuntimeSettings(BASE_DIR=Path(temporary_directory))
            source_path = Path(temporary_directory) / "scan.bin"
            database = _ImageDatabase({"doc_id": "image-1", "title": "Unreadable scan", "original_name": "scan.png", "storage_path": str(source_path), "parse_status": "processing"})
            store = _ImageStore()
            manager = PersonalKnowledgeDocumentManager(storage_path=temporary_directory, database=database, store=store, settings=settings, image_describer=failing_describer)
            source_path.write_bytes(manager._cipher.encrypt(b"image-bytes"))
            database.document["encryption_version"] = manager._cipher.VERSION
            parser = SimpleNamespace(get_supported_types=lambda: ["png"], parse_file=lambda *_: {"success": True, "content": "", "requires_vision_enrichment": True})
            with patch("modules.knowledge.personal_documents.document_parser", parser):
                result = asyncio.run(manager.process_stored_document("member-1", "image-1"))

        self.assertFalse(result["success"])
        self.assertEqual(store.calls, [])
        self.assertEqual(database.document["parse_status"], "failed")

    def test_client_file_paths_are_not_used_as_storage_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_path = Path(temporary_directory)
            manager = PersonalKnowledgeDocumentManager(storage_path=storage_path, database=object(), store=_ImageStore())
            doc_id = manager._save_document_file("member-1", b"notes", "../../outside.txt")
            stored_path = manager._storage_path("member-1", doc_id, "../../outside.txt")

            self.assertEqual(stored_path.parent, storage_path / "member-1")
            self.assertEqual(stored_path.name, f"{doc_id}.bin")
            self.assertNotEqual(stored_path.read_bytes(), b"notes")
            self.assertEqual(manager._cipher.decrypt(stored_path.read_bytes()), b"notes")


if __name__ == "__main__":
    unittest.main()

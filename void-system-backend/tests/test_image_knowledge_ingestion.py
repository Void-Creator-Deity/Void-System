"""Regression tests for the personal image knowledge ingestion path."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from api.user_document_manager import UserDocumentManager


class ImageKnowledgeIngestionTests(unittest.TestCase):
    def test_vision_description_is_indexed_and_lifecycle_completes(self) -> None:
        test_case = self

        class FakeDatabase:
            def __init__(self) -> None:
                self.document = {"doc_id": "image-1", "title": "Project board"}
                self.status_updates = []

            def get_user_document(self, user_id, doc_id):
                test_case.assertEqual(user_id, "member-1")
                test_case.assertEqual(doc_id, "image-1")
                return self.document

            def update_user_document_status(self, doc_id, status, **kwargs):
                test_case.assertEqual(doc_id, "image-1")
                self.status_updates.append((status, kwargs))
                self.document.update({"parse_status": status, **kwargs})
                return True

        class FakeVectorManager:
            def __init__(self, database) -> None:
                self.database = database
                self.calls = []

            async def process_and_store_document(self, **kwargs):
                self.calls.append(kwargs)
                self.database.update_user_document_status(
                    kwargs["doc_id"], "completed", chroma_ids=["image-vector-1"]
                )
                return {"success": True, "vector_count": 1}

        class FakeLifecycleRepository:
            def __init__(self) -> None:
                self.events = []

            def update_ingestion(self, **kwargs):
                self.events.append(kwargs)

        async def describe_image(file_data: bytes, file_name: str) -> str:
            test_case.assertEqual(file_data, b"image-bytes")
            test_case.assertEqual(file_name, "board.png")
            return "The board lists a release goal, two milestones, and a blocked deployment."

        database = FakeDatabase()
        vector_manager = FakeVectorManager(database)
        lifecycle = FakeLifecycleRepository()
        manager = UserDocumentManager(
            database=database,
            vector_manager=vector_manager,
            lifecycle_repository=lifecycle,
            image_describer=describe_image,
        )
        parser = SimpleNamespace(
            parse_file=lambda file_data, file_name: {
                "success": True,
                "content": "",
                "requires_vision_enrichment": True,
                "extraction_method": "vision_pending",
            }
        )

        with patch("api.user_document_manager.document_parser", parser):
            asyncio.run(
                manager._process_document_async(
                    "member-1", "image-1", b"image-bytes", "board.png", "job-1"
                )
            )

        self.assertEqual(len(vector_manager.calls), 1)
        self.assertEqual(
            vector_manager.calls[0]["content"],
            "The board lists a release goal, two milestones, and a blocked deployment.",
        )
        self.assertEqual(vector_manager.calls[0]["metadata"]["file_type"], "png")
        self.assertEqual(database.document["parse_status"], "completed")
        self.assertEqual(
            lifecycle.events,
            [
                {"job_id": "job-1", "owner_id": "member-1", "status": "processing"},
                {
                    "job_id": "job-1",
                    "owner_id": "member-1",
                    "status": "completed",
                    "chunk_count": 1,
                    "index_version": "legacy-chroma-v1",
                },
            ],
        )

    def test_failed_vision_description_does_not_index_the_image(self) -> None:
        test_case = self

        class FakeDatabase:
            def __init__(self) -> None:
                self.document = {"doc_id": "image-1", "title": "Unreadable scan"}
                self.status_updates = []

            def update_user_document_status(self, doc_id, status, **kwargs):
                test_case.assertEqual(doc_id, "image-1")
                self.status_updates.append((status, kwargs))
                return True

        class FakeVectorManager:
            def __init__(self) -> None:
                self.called = False

            async def process_and_store_document(self, **kwargs):
                self.called = True
                raise AssertionError("A failed image extraction must not reach the index")

        async def failing_describer(file_data: bytes, file_name: str) -> str:
            raise RuntimeError("vision service unavailable")

        database = FakeDatabase()
        vector_manager = FakeVectorManager()
        manager = UserDocumentManager(
            database=database,
            vector_manager=vector_manager,
            image_describer=failing_describer,
        )
        parser = SimpleNamespace(
            parse_file=lambda file_data, file_name: {
                "success": True,
                "content": "",
                "requires_vision_enrichment": True,
            }
        )

        with patch("api.user_document_manager.document_parser", parser):
            asyncio.run(
                manager._process_document_async(
                    "member-1", "image-1", b"image-bytes", "scan.png"
                )
            )

        self.assertFalse(vector_manager.called)
        self.assertEqual(database.status_updates[-1][0], "failed")

    def test_client_file_paths_are_not_used_as_storage_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_path = Path(temporary_directory)
            manager = UserDocumentManager(storage_path=storage_path, database=object())
            doc_id = manager._save_document_file(
                "member-1", b"notes", "../../outside.txt"
            )
            stored_path = manager._get_storage_path("member-1", doc_id, "../../outside.txt")

            self.assertEqual(stored_path.parent, storage_path / "member-1")
            self.assertEqual(stored_path.name, f"{doc_id}_outside.txt")
            self.assertEqual(stored_path.read_bytes(), b"notes")


if __name__ == "__main__":
    unittest.main()

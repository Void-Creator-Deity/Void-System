"""Regression tests for user document ingestion entry points."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.user_document_manager import UserDocumentManager


class UserDocumentManagerTests(unittest.TestCase):
    def test_invalid_upload_returns_validation_error_before_background_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manager = UserDocumentManager(
                storage_path=temporary_directory,
                database=object(),
            )
            result = asyncio.run(
                manager.upload_and_process_document(
                    user_id="member-1",
                    file_data=b"",
                    file_name="empty.txt",
                )
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "FILE_VALIDATION_FAILED")
        self.assertIn("空文件", result["message"])


    def test_rebuild_replaces_stale_vectors(self) -> None:
        class FakeDatabase:
            def __init__(self, document):
                self.document = document

            def get_user_documents(self, user_id, status=None, limit=50, offset=0):
                return [self.document]

            def get_user_document(self, user_id, doc_id):
                return self.document if doc_id == self.document["doc_id"] else None

            def update_user_document_status(self, doc_id, status, **kwargs):
                self.document["parse_status"] = status
                for key, value in kwargs.items():
                    if value is not None:
                        self.document[key] = value
                return True

        class FakeVectorManager:
            def __init__(self, database):
                self.database = database
                self.deleted = []

            def delete_document_vectors(self, user_id, doc_id):
                self.deleted.append((user_id, doc_id))
                return True

            async def process_and_store_document(self, user_id, doc_id, content, metadata):
                self.database.update_user_document_status(
                    doc_id, "completed", chroma_ids=["replacement-vector"]
                )
                return {"success": True, "vector_count": 1}

        class FakeLifecycleRepository:
            def __init__(self):
                self.events = []

            def start_ingestion(self, **kwargs):
                self.events.append(("start", kwargs))
                return {"job_id": "job-1"}

            def update_ingestion(self, **kwargs):
                self.events.append(("update", kwargs))

        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            source_path.write_text("A durable note for the rebuilt index.", encoding="utf-8")
            document = {
                "doc_id": "doc-1",
                "original_name": "notes.txt",
                "storage_path": str(source_path),
                "title": "Notes",
                "chroma_ids": ["stale-vector"],
                "parse_status": "completed",
            }
            database = FakeDatabase(document)
            vector_manager = FakeVectorManager(database)
            lifecycle_repository = FakeLifecycleRepository()
            manager = UserDocumentManager(
                storage_path=temporary_directory,
                database=database,
                vector_manager=vector_manager,
                lifecycle_repository=lifecycle_repository,
            )
            parser = SimpleNamespace(
                get_supported_types=lambda: ["txt"],
                parse_file=lambda file_data, file_name: {
                    "success": True, "content": file_data.decode("utf-8")
                }
            )
            with patch("api.user_document_manager.document_parser", parser):
                result = asyncio.run(manager.rebuild_user_index("member-1"))

        self.assertTrue(result["success"])
        self.assertEqual(result["processed_documents"], 1)
        self.assertEqual(result["failed_documents"], 0)
        self.assertEqual(result["total_vectors"], 1)
        self.assertEqual(vector_manager.deleted, [("member-1", "doc-1")])
        self.assertEqual(document["chroma_ids"], ["replacement-vector"])
        self.assertIn(
            ("update", {
                "job_id": "job-1", "owner_id": "member-1", "status": "completed",
                "chunk_count": 1, "index_version": "legacy-chroma-v1",
            }),
            lifecycle_repository.events,
        )

    def test_delete_preserves_source_when_vector_cleanup_fails(self) -> None:
        class FakeDatabase:
            def __init__(self):
                self.deleted = False
                self.document = {
                    "doc_id": "doc-1",
                    "storage_path": "missing.txt",
                    "chroma_ids": ["chunk-1"],
                }

            def check_document_exists(self, doc_id, user_id):
                return True

            def get_user_document(self, user_id, doc_id):
                return self.document

            def delete_user_document(self, doc_id, user_id):
                self.deleted = True
                return True

        class FailingVectorManager:
            def delete_document_vectors(self, user_id, doc_id):
                return False

        with tempfile.TemporaryDirectory() as temporary_directory:
            database = FakeDatabase()
            manager = UserDocumentManager(
                storage_path=temporary_directory,
                database=database,
                vector_manager=FailingVectorManager(),
            )
            result = manager.delete_document("member-1", "doc-1")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "VECTOR_DELETE_FAILED")
        self.assertFalse(database.deleted)

    def test_rebuild_keeps_existing_document_when_vector_cleanup_fails(self) -> None:
        class FakeDatabase:
            def __init__(self, document):
                self.document = document
                self.status_updates = []

            def get_user_documents(self, user_id, status=None, limit=50, offset=0):
                return [self.document]

            def get_user_document(self, user_id, doc_id):
                return self.document

            def update_user_document_status(self, doc_id, status, **kwargs):
                self.status_updates.append((doc_id, status, kwargs))
                self.document["parse_status"] = status
                return True

        class FailingVectorManager:
            def __init__(self):
                self.calls = []

            def delete_document_vectors(self, user_id, doc_id):
                self.calls.append((user_id, doc_id))
                return False

        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            source_path.write_text("Existing indexed note", encoding="utf-8")
            document = {
                "doc_id": "doc-1",
                "original_name": "notes.txt",
                "storage_path": str(source_path),
                "chroma_ids": ["previous-vector"],
                "parse_status": "completed",
            }
            database = FakeDatabase(document)
            vector_manager = FailingVectorManager()
            manager = UserDocumentManager(
                storage_path=temporary_directory,
                database=database,
                vector_manager=vector_manager,
            )
            parser = SimpleNamespace(
                get_supported_types=lambda: ["txt"],
                parse_file=lambda *args: self.fail("Parsing must not start before cleanup succeeds"),
            )
            with patch("api.user_document_manager.document_parser", parser):
                result = asyncio.run(manager.rebuild_user_index("member-1"))

        self.assertFalse(result["success"])
        self.assertEqual(result["failed_documents"], 1)
        self.assertEqual(document["parse_status"], "completed")
        self.assertEqual(database.status_updates, [])
        self.assertEqual(vector_manager.calls, [("member-1", "doc-1")])

    def test_failed_final_index_write_marks_document_retryable(self) -> None:
        class FakeDatabase:
            def __init__(self):
                self.document = {"doc_id": "doc-1", "title": "Notes", "parse_status": "parsed"}
                self.status_updates = []

            def get_user_document(self, user_id, doc_id):
                return self.document

            def update_user_document_status(self, doc_id, status, **kwargs):
                self.status_updates.append((doc_id, status, kwargs))
                self.document["parse_status"] = status
                self.document.update({key: value for key, value in kwargs.items() if value is not None})
                return True

        class FailingVectorManager:
            async def process_and_store_document(self, **kwargs):
                return {"success": False, "message": "Database status write failed"}

        with tempfile.TemporaryDirectory() as temporary_directory:
            database = FakeDatabase()
            manager = UserDocumentManager(
                storage_path=temporary_directory,
                database=database,
                vector_manager=FailingVectorManager(),
            )
            parser = SimpleNamespace(
                parse_file=lambda file_data, file_name: {"success": True, "content": "A useful note"},
            )
            with patch("api.user_document_manager.document_parser", parser):
                asyncio.run(
                    manager._process_document_async(
                        "member-1", "doc-1", b"A useful note", "notes.txt"
                    )
                )

        self.assertEqual(database.document["parse_status"], "failed")
        self.assertEqual(database.document["error_message"], "Database status write failed")


if __name__ == "__main__":
    unittest.main()

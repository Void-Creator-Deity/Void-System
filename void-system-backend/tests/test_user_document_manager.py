"""Regression tests for durable personal knowledge ingestion."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet

from core.knowledge_contracts import KnowledgeScope
from core.runtime_settings import RuntimeSettings
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from modules.knowledge.personal_documents import PersonalKnowledgeDocumentManager


class _Store:
    def __init__(self, *, failure: bool = False) -> None:
        self.failure = failure
        self.index_calls = []
        self.delete_calls = []

    def index_text(self, **kwargs):
        self.index_calls.append(kwargs)
        if self.failure:
            raise RuntimeError("index unavailable")
        return SimpleNamespace(chunk_ids=["chunk-1", "chunk-2"], collection="user_member-1_docs")

    def delete_document(self, **kwargs):
        self.delete_calls.append(kwargs)
        return True

    def stats(self, **kwargs):
        return {"collection": "user_member-1_docs", "count": 2}


class _Lifecycle:
    def __init__(self) -> None:
        self.calls = []

    def start_ingestion(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "job_id": f"job-{len(self.calls)}",
            "document_id": kwargs["document_id"],
            "status": "queued",
            "job_type": kwargs["job_type"],
        }


class _Database:
    def __init__(self, document=None) -> None:
        self.documents = {} if document is None else {document["doc_id"]: document}
        self.status_updates = []

    def add_user_document(self, **document):
        self.documents[document["doc_id"]] = dict(document)
        return True

    def get_user_document(self, user_id, doc_id):
        del user_id
        return self.documents.get(doc_id)

    def get_user_documents(self, user_id, status=None, limit=50, offset=0):
        del user_id, status, limit, offset
        return list(self.documents.values())

    def update_user_document_status(self, doc_id, status, **kwargs):
        self.status_updates.append((doc_id, status, kwargs))
        self.documents[doc_id]["parse_status"] = status
        self.documents[doc_id].update({key: value for key, value in kwargs.items() if value is not None})
        return True


def _private_storage_settings(root: Path) -> tuple[RuntimeSettings, KnowledgeSourceCipher]:
    settings = RuntimeSettings(
        BASE_DIR=root,
        DOCUMENT_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    return settings, KnowledgeSourceCipher(settings, root)


class PersonalKnowledgeDocumentManagerTests(unittest.TestCase):
    def test_invalid_upload_returns_validation_error_before_job_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=_Database(), store=_Store(), lifecycle_repository=_Lifecycle()
            )
            result = asyncio.run(manager.upload_and_process_document("member-1", b"", "empty.txt"))

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "FILE_VALIDATION_FAILED")

    def test_upload_persists_source_and_queues_durable_job_without_indexing(self) -> None:
        database = _Database()
        lifecycle = _Lifecycle()
        store = _Store()
        parser = SimpleNamespace(get_supported_types=lambda: ["txt"], extract_metadata=lambda *_: {"file_type": "txt"})
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings, cipher = _private_storage_settings(Path(temporary_directory))
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=database, store=store, lifecycle_repository=lifecycle,
                settings=settings, cipher=cipher,
            )
            with patch("modules.knowledge.personal_documents.document_parser", parser):
                result = asyncio.run(manager.upload_and_process_document("member-1", b"Durable source content", "notes.txt", tags=["work"]))
            document = database.documents[result["doc_id"]]
            self.assertEqual(cipher.decrypt(Path(document["storage_path"]).read_bytes()), b"Durable source content")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "queued")
        self.assertEqual(lifecycle.calls[0]["job_type"], "ingest")
        self.assertEqual(store.index_calls, [])

    def test_rebuild_only_queues_jobs_and_does_not_parse_or_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            settings, cipher = _private_storage_settings(Path(temporary_directory))
            source_path.write_bytes(cipher.encrypt(b"Existing indexed note"))
            database = _Database({"doc_id": "doc-1", "original_name": "notes.txt", "storage_path": str(source_path), "parse_status": "completed", "encryption_version": cipher.VERSION})
            lifecycle = _Lifecycle()
            store = _Store()
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=database, store=store, lifecycle_repository=lifecycle,
                settings=settings, cipher=cipher,
            )
            result = manager.enqueue_rebuild_jobs("member-1")

        self.assertTrue(result["success"])
        self.assertEqual(result["queued_count"], 1)
        self.assertEqual(lifecycle.calls[0]["job_type"], "rebuild")
        self.assertTrue(lifecycle.calls[0]["force"])
        self.assertEqual(store.index_calls, [])

    def test_worker_replaces_document_chunks_in_the_unified_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            settings, cipher = _private_storage_settings(Path(temporary_directory))
            source_path.write_bytes(cipher.encrypt(b"A durable note for the rebuilt index."))
            database = _Database({"doc_id": "doc-1", "title": "Notes", "original_name": "notes.txt", "storage_path": str(source_path), "parse_status": "processing", "encryption_version": cipher.VERSION})
            store = _Store()
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=database, store=store, settings=settings, cipher=cipher,
            )
            parser = SimpleNamespace(get_supported_types=lambda: ["txt"], parse_file=lambda data, _: {"success": True, "content": data.decode("utf-8")})
            progress = []
            with patch("modules.knowledge.personal_documents.document_parser", parser):
                result = asyncio.run(manager.process_stored_document("member-1", "doc-1", report_progress=lambda stage, value: progress.append((stage, value)) or True))

        self.assertTrue(result["success"])
        self.assertEqual(result["chunk_count"], 2)
        self.assertEqual(database.documents["doc-1"]["parse_status"], "completed")
        self.assertEqual(store.index_calls[0]["scope"], KnowledgeScope.USER)
        self.assertEqual(store.index_calls[0]["document_id"], "doc-1")
        self.assertIn(("finalizing", 95), progress)

    def test_worker_marks_source_failed_when_unified_store_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            settings, cipher = _private_storage_settings(Path(temporary_directory))
            source_path.write_bytes(cipher.encrypt(b"A useful note"))
            database = _Database({"doc_id": "doc-1", "title": "Notes", "original_name": "notes.txt", "storage_path": str(source_path), "parse_status": "processing", "encryption_version": cipher.VERSION})
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=database, store=_Store(failure=True), settings=settings, cipher=cipher,
            )
            parser = SimpleNamespace(get_supported_types=lambda: ["txt"], parse_file=lambda *_: {"success": True, "content": "A useful note"})
            with patch("modules.knowledge.personal_documents.document_parser", parser):
                result = asyncio.run(manager.process_stored_document("member-1", "doc-1"))

        self.assertFalse(result["success"])
        self.assertEqual(database.documents["doc-1"]["parse_status"], "failed")
        self.assertEqual(database.documents["doc-1"]["error_message"], "Document processing failed")

    def test_worker_marks_source_cancelled_when_the_durable_job_requests_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "notes.txt"
            settings, cipher = _private_storage_settings(Path(temporary_directory))
            source_path.write_bytes(cipher.encrypt(b"A useful note"))
            database = _Database({"doc_id": "doc-1", "title": "Notes", "original_name": "notes.txt", "storage_path": str(source_path), "parse_status": "processing", "encryption_version": cipher.VERSION})
            manager = PersonalKnowledgeDocumentManager(
                storage_path=temporary_directory, database=database, store=_Store(), settings=settings, cipher=cipher,
            )
            result = asyncio.run(manager.process_stored_document(
                "member-1", "doc-1", report_progress=lambda _stage, _progress: False,
            ))

        self.assertTrue(result["cancelled"])
        self.assertEqual(database.documents["doc-1"]["parse_status"], "cancelled")


if __name__ == "__main__":
    unittest.main()

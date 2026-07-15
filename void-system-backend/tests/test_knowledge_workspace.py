"""Personal Knowledge Workspace retention and retrieval tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from adapters.legacy.knowledge_adapters import LegacyUserVectorIndex
from adapters.sqlite.user_knowledge_repository import SQLiteUserKnowledgeRepository
from core.knowledge_contracts import KnowledgeQuery
from database import Database
from modules.knowledge.workspace import KnowledgeWorkspace


class FakeLifecycle:
    def latest_ingestion(self, *, document_id: str, owner_id: str):
        return {"document_id": document_id, "owner_id": owner_id, "status": "completed"}


class FakeMaintenance:
    def __init__(self, delete_result: bool = True) -> None:
        self.delete_result = delete_result
        self.deleted = []

    async def rebuild_index(self, owner_id: str):
        return {"success": True, "owner_id": owner_id}

    def index_stats(self, owner_id: str):
        return {"owner_id": owner_id}

    def delete_indexed_document(self, owner_id: str, document_id: str) -> bool:
        self.deleted.append((owner_id, document_id))
        return self.delete_result


class KnowledgeWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "knowledge.db")
        connection = self.database.get_connection()
        try:
            connection.execute(
                "INSERT INTO users (user_id, username, email) VALUES ('u1', 'user-one', 'u1@example.com')"
            )
            connection.execute(
                """INSERT INTO user_documents
                   (doc_id, user_id, title, original_name, file_size, storage_path,
                    parse_status, tags, chroma_ids)
                   VALUES ('d1', 'u1', 'Guide', 'guide.md', 12, '', 'completed', '["work"]', '[]')"""
            )
            connection.commit()
        finally:
            connection.close()
        self.repository = SQLiteUserKnowledgeRepository(self.database.get_connection)
        self.maintenance = FakeMaintenance()
        self.workspace = KnowledgeWorkspace(
            self.repository, self.maintenance, FakeLifecycle()
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_archive_hides_document_and_restore_makes_it_retrievable(self) -> None:
        self.assertEqual(self.repository.active_document_ids("u1"), ["d1"])
        self.assertTrue(self.workspace.archive_document("u1", "d1"))
        self.assertEqual(self.repository.active_document_ids("u1"), [])
        archived = self.workspace.list_documents("u1", retention="archived")
        self.assertEqual(archived["pagination"]["total"], 1)
        self.assertTrue(archived["documents"][0]["is_archived"])
        self.assertEqual(archived["stats"]["archived_documents"], 1)

        self.assertTrue(self.workspace.restore_document("u1", "d1"))
        self.assertEqual(self.repository.active_document_ids("u1"), ["d1"])

    def test_permanent_purge_requires_archive_and_index_cleanup(self) -> None:
        self.assertEqual(
            self.workspace.purge_document("u1", "d1"),
            {"purged": False, "reason": "not_found"},
        )
        self.workspace.archive_document("u1", "d1")
        result = self.workspace.purge_document("u1", "d1")
        self.assertTrue(result["purged"])
        self.assertEqual(self.maintenance.deleted, [("u1", "d1")])
        self.assertIsNone(
            self.repository.get_document("u1", "d1", include_archived=True)
        )

    def test_failed_index_cleanup_keeps_archived_metadata(self) -> None:
        maintenance = FakeMaintenance(delete_result=False)
        workspace = KnowledgeWorkspace(self.repository, maintenance, FakeLifecycle())
        workspace.archive_document("u1", "d1")
        self.assertEqual(
            workspace.purge_document("u1", "d1"),
            {"purged": False, "reason": "index_unavailable"},
        )
        self.assertIsNotNone(
            self.repository.get_document("u1", "d1", include_archived=True)
        )


class ActiveRetrievalTests(unittest.TestCase):
    def test_vector_search_uses_only_active_catalog_ids(self) -> None:
        class Repository:
            def active_document_ids(self, owner_id, requested_ids=None):
                self.call = (owner_id, requested_ids)
                return ["active-doc"]

        class Document:
            page_content = "supported text"
            metadata = {"doc_id": "active-doc", "chunk_id": "chunk-1"}

        class Collection:
            def similarity_search_with_relevance_scores(self, **kwargs):
                self.kwargs = kwargs
                return [(Document(), 0.9)]

        class VectorManager:
            def __init__(self):
                self.collection = Collection()

            def get_user_collection(self, owner_id):
                return self.collection

        repository = Repository()
        manager = VectorManager()
        index = LegacyUserVectorIndex(manager, repository)
        results = index.search(
            KnowledgeQuery(owner_id="u1", question="question", document_ids=["active-doc", "archived-doc"])
        )
        self.assertEqual(repository.call, ("u1", ["active-doc", "archived-doc"]))
        self.assertEqual(
            manager.collection.kwargs["filter"],
            {"doc_id": {"$in": ["active-doc"]}},
        )
        self.assertEqual([chunk.document_id for chunk in results], ["active-doc"])


if __name__ == "__main__":
    unittest.main()

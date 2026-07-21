"""Personal Knowledge Workspace retention and retrieval tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from core.knowledge_contracts import KnowledgeChunk, KnowledgeScope
from modules.knowledge.indexes import ScopedSemanticIndex
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
                """INSERT INTO knowledge_documents
                   (document_id, visibility, owner_id, title, file_name, file_size, storage_path,
                    encryption_version, parse_status, tags, chroma_ids)
                   VALUES ('d1', 'private', 'u1', 'Guide', 'guide.md', 12, '', 'none', 'completed', '["work"]', '[]')"""
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
    def test_semantic_search_receives_only_active_catalog_documents(self) -> None:
        class Store:
            def semantic_search(self, *, query, scope, catalog):
                self.call = (query, scope, catalog)
                return [KnowledgeChunk("chunk-1", "active-doc", "u1", "supported text", scope, 0.9)]

        class Repository:
            def active_document_ids(self, owner_id, requested_ids=None):
                self.call = (owner_id, requested_ids)
                return ["active-doc"]

            def get_document(self, owner_id, document_id):
                return {"doc_id": document_id, "title": "Guide", "original_name": "guide.md"}

        repository = Repository()
        store = Store()

        def catalog(query, scope):
            if scope != KnowledgeScope.USER or not query.owner_id:
                return {}
            return {document_id: repository.get_document(query.owner_id, document_id) for document_id in repository.active_document_ids(query.owner_id, query.document_ids)}

        index = ScopedSemanticIndex(store, catalog)
        results = index.search(KnowledgeQuery(owner_id="u1", question="question", document_ids=["active-doc", "archived-doc"], scopes=(KnowledgeScope.USER,)))
        self.assertEqual(repository.call, ("u1", ["active-doc", "archived-doc"]))
        self.assertEqual(store.call[1], KnowledgeScope.USER)
        self.assertEqual(set(store.call[2]), {"active-doc"})
        self.assertEqual([chunk.document_id for chunk in results], ["active-doc"])


if __name__ == "__main__":
    unittest.main()

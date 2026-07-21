"""Regression coverage for shared material references in a user's library."""
from pathlib import Path
import tempfile
import unittest

from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from database import Database


class UserLibraryEntryTests(unittest.TestCase):
    """Verify join references affect eligibility without duplicating shared material."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "library.db")
        self.catalog = SQLiteKnowledgeDocumentRepository(self.database.get_connection)
        self.owner_id = "member-1"
        self.catalog.create_document(
            visibility="private",
            document_id="private-1",
            owner_id=self.owner_id,
            title="Private notes",
            file_name="private.txt",
            file_type="txt",
            file_size=16,
            parse_status="completed",
            content_preview="private content",
        )
        self.catalog.create_document(
            visibility="official",
            document_id="shared-1",
            owner_id="system",
            title="Shared handbook",
            file_name="handbook.txt",
            file_type="txt",
            file_size=18,
            parse_status="completed",
            content_preview="shared content",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_join_is_a_reference_not_a_second_document(self) -> None:
        """Joining creates one user entry while the shared catalogue entity remains single-copy."""
        self.assertTrue(self.catalog.add_shared_document_to_library(
            owner_id=self.owner_id,
            document_id="shared-1",
        ))
        self.assertTrue(self.catalog.add_shared_document_to_library(
            owner_id=self.owner_id,
            document_id="shared-1",
        ))
        connection = self.database.get_connection()
        try:
            document_count = connection.execute(
                "SELECT COUNT(*) FROM knowledge_documents WHERE document_id = 'shared-1'"
            ).fetchone()[0]
            entry_count = connection.execute(
                "SELECT COUNT(*) FROM user_library_entries WHERE user_id = ? AND document_id = 'shared-1'",
                (self.owner_id,),
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(document_count, 1)
        self.assertEqual(entry_count, 1)

    def test_default_catalog_excludes_unjoined_shared_material(self) -> None:
        """Default retrieval sees private uploads and joined shared material only."""
        before_join = self.catalog.active_library_catalog(owner_id=self.owner_id)
        self.assertEqual(set(before_join), {"private-1"})

        self.catalog.add_shared_document_to_library(owner_id=self.owner_id, document_id="shared-1")
        after_join = self.catalog.active_library_catalog(owner_id=self.owner_id)
        self.assertEqual(set(after_join), {"private-1", "shared-1"})

        self.assertTrue(self.catalog.remove_shared_document_from_library(
            owner_id=self.owner_id,
            document_id="shared-1",
        ))
        after_remove = self.catalog.active_library_catalog(owner_id=self.owner_id)
        self.assertEqual(set(after_remove), {"private-1"})

    def test_global_search_expands_only_when_requested(self) -> None:
        """The explicit global flag exposes shared material without altering the saved library."""
        library_documents = self.catalog.list_documents(owner_id=self.owner_id, source="library")
        shared_documents = self.catalog.list_documents(owner_id=self.owner_id, source="shared")
        global_catalog = self.catalog.active_library_catalog(
            owner_id=self.owner_id,
            include_global_shared=True,
        )

        self.assertEqual([item["document_id"] for item in library_documents["documents"]], ["private-1"])
        self.assertEqual(shared_documents["documents"][0]["library_state"], "shared_available")
        self.assertEqual(set(global_catalog), {"private-1", "shared-1"})


if __name__ == "__main__":
    unittest.main()

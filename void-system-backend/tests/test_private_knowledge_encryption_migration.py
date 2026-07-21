"""Regression coverage for private knowledge encryption migrations without Chroma."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from modules.knowledge.personal_documents import PersonalKnowledgeDocumentManager


class PrivateKnowledgeEncryptionMigrationTests(unittest.TestCase):
    def _settings(self, root: Path, *, key: str = "") -> RuntimeSettings:
        return RuntimeSettings(BASE_DIR=root, DOCUMENT_ENCRYPTION_KEY=key)

    def test_retired_development_key_is_moved_to_canonical_location(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            legacy_path = root / "user_documents" / ".keys" / "document-fernet.key"
            legacy_path.parent.mkdir(parents=True)
            legacy_key = Fernet.generate_key()
            legacy_path.write_bytes(legacy_key + b"\n")

            cipher = KnowledgeSourceCipher(self._settings(root), root / "user_documents")
            canonical_path = root / ".keys" / "document-fernet.key"

            self.assertTrue(canonical_path.is_file())
            self.assertFalse(legacy_path.exists())
            self.assertEqual(canonical_path.read_bytes().strip(), legacy_key)
            self.assertEqual(cipher.decrypt(cipher.encrypt(b"private source")), b"private source")

    def test_encrypted_legacy_filename_is_moved_to_opaque_managed_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings = self._settings(root, key=Fernet.generate_key().decode("ascii"))
            cipher = KnowledgeSourceCipher(settings, root / "user_documents")
            database = Database(root / "knowledge.db")
            catalog = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)
            owner_id = "member-1"
            document_id = "doc-1"
            legacy_path = root / "user_documents" / owner_id / "doc-1_original-notes.txt"
            legacy_path.parent.mkdir(parents=True)
            legacy_path.write_bytes(cipher.encrypt(b"private source fixture"))
            catalog.create_document(
                visibility="private",
                document_id=document_id,
                owner_id=owner_id,
                title="Notes",
                file_name="original-notes.txt",
                file_type="txt",
                file_size=22,
                storage_path=str(legacy_path),
                encryption_version=cipher.VERSION,
            )

            manager = PersonalKnowledgeDocumentManager(
                database=database,
                store=None,
                settings=settings,
                storage_path=str(root / "user_documents"),
                cipher=cipher,
                document_repository=catalog,
            )
            result = manager.migrate_private_source_storage()
            migrated = catalog.get_document(
                visibility="private", document_id=document_id, owner_id=owner_id, viewer_id=owner_id
            )
            canonical_path = root / "user_documents" / owner_id / "doc-1.bin"

            self.assertEqual(result["migrated_count"], 0)
            self.assertEqual(result["relocated_count"], 1)
            self.assertEqual(result["already_secure_count"], 1)
            self.assertEqual(result["failed"], [])
            self.assertFalse(legacy_path.exists())
            self.assertTrue(canonical_path.is_file())
            self.assertEqual(migrated["encryption_version"], cipher.VERSION)
            self.assertEqual(Path(migrated["storage_path"]).resolve(), canonical_path.resolve())
            self.assertEqual(cipher.decrypt(canonical_path.read_bytes()), b"private source fixture")

    def test_plaintext_private_preview_is_migrated_and_not_returned_before_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings = self._settings(root, key=Fernet.generate_key().decode("ascii"))
            cipher = KnowledgeSourceCipher(settings, root / "user_documents")
            database = Database(root / "knowledge.db")
            catalog = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)
            catalog.create_document(
                visibility="private",
                document_id="doc-1",
                owner_id="member-1",
                title="Notes",
                file_name="notes.txt",
                file_type="txt",
                file_size=3,
                encryption_version=cipher.VERSION,
            )
            connection = database.get_connection()
            try:
                connection.execute(
                    "UPDATE knowledge_documents SET content_preview = ? WHERE document_id = ?",
                    ("legacy plaintext preview", "doc-1"),
                )
                connection.commit()
            finally:
                connection.close()

            hidden = catalog.get_document(
                visibility="private", document_id="doc-1", owner_id="member-1", viewer_id="member-1"
            )
            result = catalog.migrate_legacy_private_previews()
            connection = database.get_connection()
            try:
                stored = connection.execute(
                    "SELECT content_preview FROM knowledge_documents WHERE document_id = ?",
                    ("doc-1",),
                ).fetchone()[0]
            finally:
                connection.close()
            revealed = catalog.get_document(
                visibility="private", document_id="doc-1", owner_id="member-1", viewer_id="member-1"
            )

        self.assertEqual(hidden["content_preview"], "")
        self.assertEqual(result, {"migrated_count": 1, "failed": []})
        self.assertNotIn("legacy plaintext preview", stored)
        self.assertTrue(str(stored).startswith("enc:fernet-v1:"))
        self.assertEqual(revealed["content_preview"], "legacy plaintext preview")


if __name__ == "__main__":
    unittest.main()

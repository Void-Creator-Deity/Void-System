"""Regression tests for private knowledge encryption at rest."""
from __future__ import annotations

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chromadb
from chromadb.api.client import SharedSystemClient
from cryptography.fernet import Fernet

from adapters.chroma.knowledge_store import ChromaKnowledgeStore
from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from modules.knowledge.personal_documents import PersonalKnowledgeDocumentManager


class _Store:
    """Minimal non-indexing store for source-file encryption coverage."""



class _Embeddings:
    """Small deterministic embedding stub for Chroma encryption coverage."""

    def embed_documents(self, values):
        return [[float(len(value)), 1.0, 0.0] for value in values]

    def embed_query(self, value):
        return [float(len(value)), 1.0, 0.0]


class PrivateKnowledgeEncryptionTests(unittest.TestCase):
    def _settings(self, root: Path) -> RuntimeSettings:
        return RuntimeSettings(
            BASE_DIR=root,
            CHROMA_PERSIST_DIR="chroma",
            DOCUMENT_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
        )

    def test_private_chroma_body_is_ciphertext_but_retrieval_returns_plaintext(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        store = None
        client = None
        collection = None
        try:
            root = Path(temporary_directory.name)
            settings = self._settings(root)
            cipher = KnowledgeSourceCipher(settings, root / "user_documents")
            with patch("adapters.chroma.knowledge_store.get_embeddings", return_value=_Embeddings()):
                store = ChromaKnowledgeStore(settings, cipher=cipher)
                store.index_text(
                    scope=KnowledgeScope.USER,
                    owner_id="member-1",
                    document_id="doc-1",
                    text="Private launch sequence: amber moon",
                    metadata={"title": "Sensitive title", "file_name": "secret-notes.txt", "file_type": "txt"},
                )
                client = chromadb.PersistentClient(path=str(settings.get_chroma_path()))
                collection = client.get_collection(store.collection_name(KnowledgeScope.USER, "member-1"))
                raw = collection.get(include=["documents", "metadatas"])
                stored = str(raw["documents"][0])
                self.assertNotIn("Private launch sequence", stored)
                self.assertEqual(raw["metadatas"][0]["content_encryption"], cipher.VERSION)
                self.assertNotIn("title", raw["metadatas"][0])
                self.assertNotIn("file_name", raw["metadatas"][0])

                catalog = {"doc-1": {"title": "Sensitive title", "file_name": "secret-notes.txt", "tags": []}}
                query = KnowledgeQuery(owner_id="member-1", question="launch", top_k=3)
                semantic = store.semantic_search(query=query, scope=KnowledgeScope.USER, catalog=catalog)
                lexical = store.lexical_search(query=query, scope=KnowledgeScope.USER, catalog=catalog)
        finally:
            if store is not None:
                store.close()
            if client is not None:
                client.close()
            collection = None
            store = None
            client = None
            SharedSystemClient.clear_system_cache()
            gc.collect()
            temporary_directory.cleanup()

        self.assertEqual(semantic[0].text, "Private launch sequence: amber moon")
        self.assertEqual(lexical[0].text, "Private launch sequence: amber moon")

    def test_manager_direct_composition_encrypts_source_and_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings = self._settings(root)
            database = Database(root / "knowledge.db")
            cipher = KnowledgeSourceCipher(settings, root / "user_documents")
            manager = PersonalKnowledgeDocumentManager(
                database=database,
                store=_Store(),
                settings=settings,
                storage_path=str(root / "user_documents"),
                cipher=cipher,
            )
            document_id = manager._save_document_file("member-1", b"source must stay private", "notes.txt")
            stored_path = manager._storage_path("member-1", document_id, "notes.txt")
            manager._catalog.create_document(
                visibility="private",
                document_id=document_id,
                owner_id="member-1",
                title="Notes",
                file_name="notes.txt",
                file_type="txt",
                file_size=24,
                encryption_version=cipher.VERSION,
            )
            manager._set_private_status(
                "member-1", document_id, "completed", content_preview="preview must stay private"
            )
            raw_source = stored_path.read_bytes()
            connection = database.get_connection()
            try:
                raw_preview = connection.execute(
                    "SELECT content_preview FROM knowledge_documents WHERE document_id = ?",
                    (document_id,),
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertNotIn(b"source must stay private", raw_source)
        self.assertEqual(cipher.decrypt(raw_source), b"source must stay private")
        self.assertNotIn("preview must stay private", raw_preview)
        self.assertTrue(str(raw_preview).startswith("enc:fernet-v1:"))

    def test_private_preview_is_not_persisted_as_plaintext(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings = self._settings(root)
            database = Database(root / "knowledge.db")
            cipher = KnowledgeSourceCipher(settings, root / "user_documents")
            catalog = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)
            catalog.create_document(
                visibility="private",
                document_id="doc-1",
                owner_id="member-1",
                title="Notes",
                file_name="notes.txt",
                file_type="txt",
                file_size=4,
                encryption_version=cipher.VERSION,
            )
            catalog.set_processing_state(
                visibility="private",
                document_id="doc-1",
                owner_id="member-1",
                parse_status="completed",
                content_preview="Sensitive preview text",
            )
            connection = database.get_connection()
            try:
                stored = connection.execute(
                    "SELECT content_preview FROM knowledge_documents WHERE document_id = 'doc-1'"
                ).fetchone()[0]
            finally:
                connection.close()
            revealed = catalog.get_document(
                visibility="private", document_id="doc-1", owner_id="member-1", viewer_id="member-1"
            )

        self.assertNotIn("Sensitive preview text", stored)
        self.assertTrue(str(stored).startswith("enc:fernet-v1:"))
        self.assertEqual(revealed["content_preview"], "Sensitive preview text")


if __name__ == "__main__":
    unittest.main()

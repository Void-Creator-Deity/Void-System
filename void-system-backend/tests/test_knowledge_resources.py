"""Knowledge resource composition tests without external model dependencies."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import ANY, patch

from cryptography.fernet import Fernet

from core.runtime_settings import RuntimeSettings
from modules.knowledge.service import create_user_knowledge_resources


class KnowledgeResourceCompositionTests(unittest.TestCase):
    def test_resources_use_one_store_for_documents_and_retrieval(self) -> None:
        class FakeDatabase:
            def get_connection(self):
                return object()

        database = FakeDatabase()
        settings = RuntimeSettings(
            BASE_DIR=Path("."),
            DOCUMENT_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
        )
        fake_store = type("Store", (), {"migrate_legacy_shared_collection": lambda self, catalog: {"migrated": False}})()
        fake_lifecycle = object()
        fake_repository = object()
        fake_documents = object()
        fake_shared = type("Shared", (), {"active_catalog": lambda self: {}})()
        fake_workspace = object()
        fake_engine = object()

        with patch("modules.knowledge.service.ChromaKnowledgeStore", return_value=fake_store) as store_factory, patch(
            "modules.knowledge.service.SQLiteKnowledgeLifecycleRepository", return_value=fake_lifecycle
        ), patch(
            "modules.knowledge.service.SQLiteUserKnowledgeRepository", return_value=fake_repository
        ), patch(
            "modules.knowledge.service.PersonalKnowledgeDocumentManager", return_value=fake_documents
        ) as documents_factory, patch(
            "modules.knowledge.service.SharedKnowledgeDocumentManager", return_value=fake_shared
        ) as shared_factory, patch(
            "modules.knowledge.service.KnowledgeWorkspace", return_value=fake_workspace
        ) as workspace_factory, patch(
            "modules.knowledge.service._engine", return_value=fake_engine
        ) as engine_factory:
            resources = create_user_knowledge_resources(database, settings)

        self.assertIs(resources.engine, fake_engine)
        self.assertIs(resources.workspace, fake_workspace)
        self.assertIs(resources.document_manager, fake_documents)
        store_factory.assert_called_once_with(settings, cipher=ANY)
        documents_factory.assert_called_once_with(
            database=database,
            store=fake_store,
            lifecycle_repository=fake_lifecycle,
            settings=settings,
            cipher=ANY,
            document_repository=ANY,
        )
        shared_factory.assert_called_once_with(database=database, store=fake_store, document_repository=ANY)
        workspace_factory.assert_called_once_with(fake_repository, fake_documents, fake_lifecycle)
        engine_factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()

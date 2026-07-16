"""Knowledge resource composition tests that avoid optional runtime dependencies."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from modules.knowledge.service import create_user_knowledge_resources


class KnowledgeResourceCompositionTests(unittest.TestCase):
    def test_resources_share_application_database_behind_modules(self) -> None:
        class FakeDatabase:
            def get_connection(self):
                raise AssertionError("The composition test does not open a connection")

        database = FakeDatabase()
        fake_engine = object()
        fake_repository = object()
        fake_lifecycle = object()
        fake_maintenance = object()
        fake_workspace = object()

        class FakeVectorManager:
            def __init__(self, database):
                self.database = database

        class FakeDocumentManager:
            def __init__(self, database, vector_manager, lifecycle_repository):
                self.database = database
                self.vector_manager = vector_manager
                self.lifecycle_repository = lifecycle_repository

        fake_vector_module = types.ModuleType("api.user_vector_manager")
        fake_vector_module.UserVectorManager = FakeVectorManager
        fake_document_module = types.ModuleType("api.user_document_manager")
        fake_document_module.UserDocumentManager = FakeDocumentManager

        with patch.dict(
            sys.modules,
            {
                "api.user_vector_manager": fake_vector_module,
                "api.user_document_manager": fake_document_module,
            },
        ), patch(
            "modules.knowledge.service.SQLiteKnowledgeLifecycleRepository",
            return_value=fake_lifecycle,
        ), patch(
            "modules.knowledge.service.SQLiteUserKnowledgeRepository",
            return_value=fake_repository,
        ), patch(
            "modules.knowledge.service.LegacyUserKnowledgeMaintenance",
            return_value=fake_maintenance,
        ) as maintenance_adapter, patch(
            "modules.knowledge.service.KnowledgeWorkspace",
            return_value=fake_workspace,
        ) as workspace_module, patch(
            "modules.knowledge.service.build_legacy_user_knowledge_engine",
            return_value=fake_engine,
        ) as build_engine:
            resources = create_user_knowledge_resources(database)

        self.assertIs(resources.engine, fake_engine)
        self.assertIs(resources.workspace, fake_workspace)
        self.assertIs(resources.lifecycle_repository, fake_lifecycle)
        document_manager, vector_manager = maintenance_adapter.call_args.args
        self.assertIs(document_manager.database, database)
        self.assertIs(vector_manager.database, database)
        self.assertIs(document_manager.vector_manager, vector_manager)
        self.assertIs(document_manager.lifecycle_repository, fake_lifecycle)
        workspace_module.assert_called_once_with(
            fake_repository, fake_maintenance, fake_lifecycle
        )
        build_engine.assert_called_once_with(
            document_manager,
            vector_manager,
            fake_repository,
            trace_recorder=fake_lifecycle,
            use_recorder=fake_lifecycle,
        )


if __name__ == "__main__":
    unittest.main()

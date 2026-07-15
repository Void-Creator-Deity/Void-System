"""HTTP contract checks for the personal Knowledge Workspace."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from api.http.dependencies import get_user_knowledge_workspace
from core.runtime_settings import RuntimeSettings


class FakeWorkspace:
    def __init__(self) -> None:
        self.archived = []
        self.restored = []
        self.purged = []

    def list_documents(self, owner_id, **filters):
        return {
            "documents": [],
            "pagination": {"limit": filters["limit"], "offset": filters["offset"], "total": 0, "has_more": False},
            "stats": self.stats(owner_id),
            "retention": filters["retention"],
        }

    def stats(self, owner_id):
        return {
            "total_documents": 0,
            "completed_documents": 0,
            "archived_documents": 1,
            "status_stats": {},
            "total_size": 0,
        }

    def archive_document(self, owner_id, document_id):
        self.archived.append((owner_id, document_id))
        return True

    def restore_document(self, owner_id, document_id):
        self.restored.append((owner_id, document_id))
        return True

    def purge_document(self, owner_id, document_id):
        self.purged.append((owner_id, document_id))
        return {"purged": True, "file_deleted": True}


class KnowledgeWorkspaceHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = RuntimeSettings(
            BOOTSTRAP_ADMIN_ENABLED=True,
            DEFAULT_ADMIN_USERNAME="admin",
            DEFAULT_ADMIN_EMAIL="admin@example.com",
            DEFAULT_ADMIN_PASSWORD="admin-password-2026",
        )
        self.app = create_app(
            ApplicationOptions(
                database_path=str(Path(self.temp_dir.name) / "documents.db"),
                enable_ai_routes=False,
                enable_langserve_routes=False,
                settings=settings,
            )
        )
        self.workspace = FakeWorkspace()
        self.app.dependency_overrides[get_user_knowledge_workspace] = lambda: self.workspace
        self.client = TestClient(self.app)
        self.client.__enter__()
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": "admin", "password": "admin-password-2026"},
        )
        self.headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_list_accepts_explicit_retention_view(self) -> None:
        response = self.client.get(
            "/api/user/documents?retention=archived&limit=10&offset=0",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["retention"], "archived")

    def test_archive_restore_and_purge_have_distinct_contracts(self) -> None:
        archived = self.client.delete("/api/user/documents/doc-1", headers=self.headers)
        restored = self.client.post("/api/user/documents/doc-1/restore", headers=self.headers)
        purged = self.client.delete("/api/user/documents/doc-1/purge", headers=self.headers)

        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["data"], {"retention": "archived", "restorable": True})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["data"], {"retention": "active"})
        self.assertEqual(purged.status_code, 200)
        self.assertTrue(purged.json()["data"]["purged"])
        owner_id = self.workspace.archived[0][0]
        self.assertEqual(self.workspace.archived, [(owner_id, "doc-1")])
        self.assertEqual(self.workspace.restored, [(owner_id, "doc-1")])
        self.assertEqual(self.workspace.purged, [(owner_id, "doc-1")])

    def test_workspace_reads_do_not_load_optional_retrieval_infrastructure(self) -> None:
        self.app.dependency_overrides.pop(get_user_knowledge_workspace)
        with patch(
            "modules.knowledge.service._create_legacy_user_knowledge_managers",
            side_effect=AssertionError("retrieval infrastructure loaded"),
        ):
            response = self.client.get(
                "/api/user/documents?retention=archived",
                headers=self.headers,
            )
            activity_response = self.client.get(
                "/api/user/knowledge/activity",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["pagination"]["total"], 0)
        self.assertEqual(activity_response.status_code, 200)
        self.assertEqual(activity_response.json()["data"]["activity"], [])


if __name__ == "__main__":
    unittest.main()

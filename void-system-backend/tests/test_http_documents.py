"""HTTP contract checks for the personal Knowledge Workspace."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository
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
                enable_knowledge_job_worker=False,
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
            "modules.knowledge.service.ChromaKnowledgeStore",
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


    def test_knowledge_job_endpoints_expose_durable_public_state(self) -> None:
        connection = self.app.state.database.get_connection()
        try:
            owner_id = connection.execute(
                "SELECT user_id FROM users WHERE username = ?", ("admin",)
            ).fetchone()["user_id"]
        finally:
            connection.close()
        repository = SQLiteKnowledgeLifecycleRepository(self.app.state.database.get_connection)
        started = repository.start_ingestion(
            document_id="doc-http-1",
            owner_id=owner_id,
            content_fingerprint="http-source",
            source_size=12,
            index_version="test-index-v1",
        )

        listed = self.client.get("/api/user/knowledge/jobs", headers=self.headers)
        fetched = self.client.get(
            f"/api/user/knowledge/jobs/{started['job_id']}", headers=self.headers
        )
        cancelled = self.client.post(
            f"/api/user/knowledge/jobs/{started['job_id']}/cancel", headers=self.headers
        )
        retried = self.client.post(
            f"/api/user/knowledge/jobs/{started['job_id']}/retry", headers=self.headers
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["jobs"][0]["job_id"], started["job_id"])
        self.assertNotIn("lease_token", listed.json()["data"]["jobs"][0])
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["data"]["status"], "queued")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(retried.json()["data"]["status"], "queued")
        self.assertNotEqual(retried.json()["data"]["job_id"], started["job_id"])

        active_retry = self.client.post(
            f"/api/user/knowledge/jobs/{retried.json()['data']['job_id']}/retry",
            headers=self.headers,
        )
        self.assertEqual(active_retry.status_code, 409)
        self.assertEqual(active_retry.json()["error_code"], "KNOWLEDGE_JOB_NOT_RETRYABLE")

    def test_unknown_knowledge_job_returns_not_found(self) -> None:
        response = self.client.get(
            "/api/user/knowledge/jobs/missing-job", headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "KNOWLEDGE_JOB_NOT_FOUND")

    def test_library_tags_default_to_the_unified_library_scope(self) -> None:
        """The tags endpoint must not send the retired all-library scope to the catalogue."""
        response = self.client.get("/api/library/tags", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"tags": []})


if __name__ == "__main__":
    unittest.main()

"""Regression coverage for knowledge-index outage visibility."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from fastapi.testclient import TestClient

from modules.knowledge.indexes import ScopedLexicalIndex, ScopedSemanticIndex
from api.http.application import ApplicationOptions, create_app
from api.http.dependencies import get_user_knowledge_resources
from core.knowledge_contracts import KnowledgeQuery, KnowledgeRetrievalError, KnowledgeScope
from core.runtime_settings import RuntimeSettings


class _BrokenStore:
    def semantic_search(self, *, query, scope, catalog):
        del query, catalog
        raise KnowledgeRetrievalError(f"{scope.value}_semantic")

    def lexical_search(self, *, query, scope, catalog):
        del query, catalog
        raise KnowledgeRetrievalError(f"{scope.value}_lexical")


def _catalog(query, scope):
    del query
    prefix = "user" if scope == KnowledgeScope.USER else "system"
    return {f"{prefix}-document": {"title": "Runbook", "file_name": "runbook.md", "tags": []}}


class KnowledgeRetrievalFailureTests(unittest.TestCase):
    """Ensure store outages remain distinct from a normal no-result search."""

    def test_user_semantic_failure_is_not_an_empty_result(self) -> None:
        index = ScopedSemanticIndex(_BrokenStore(), _catalog)

        with self.assertRaisesRegex(KnowledgeRetrievalError, "user_semantic"):
            index.search(KnowledgeQuery(owner_id="user-1", question="What changed?"))

    def test_user_lexical_failure_is_not_an_empty_result(self) -> None:
        index = ScopedLexicalIndex(_BrokenStore(), _catalog)

        with self.assertRaisesRegex(KnowledgeRetrievalError, "user_lexical"):
            index.search(KnowledgeQuery(owner_id="user-1", question="What changed?"))

    def test_shared_semantic_and_lexical_failures_are_visible(self) -> None:
        query = KnowledgeQuery(
            question="How do I recover?",
            scopes=(KnowledgeScope.SYSTEM,),
        )

        with self.assertRaisesRegex(KnowledgeRetrievalError, "system_semantic"):
            ScopedSemanticIndex(_BrokenStore(), _catalog).search(query)
        with self.assertRaisesRegex(KnowledgeRetrievalError, "system_lexical"):
            ScopedLexicalIndex(_BrokenStore(), _catalog).search(query)


class _FailingEngine:
    def search(self, query):
        del query
        raise KnowledgeRetrievalError("user_vector")


class _Resources:
    def __init__(self) -> None:
        self.engine = _FailingEngine()


class KnowledgeRetrievalHttpTests(unittest.TestCase):
    """Verify HTTP does not present an index outage as an empty search response."""

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
                database_path=str(Path(self.temp_dir.name) / "knowledge-failures.db"),
                enable_ai_routes=False,
                enable_langserve_routes=False,
                settings=settings,
            )
        )
        self.app.dependency_overrides[get_user_knowledge_resources] = lambda: _Resources()
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

    def test_user_search_returns_recoverable_service_error(self) -> None:
        response = self.client.post(
            "/api/knowledge/search",
            headers=self.headers,
            json={"query": "What changed?", "top_k": 3},
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error_code"], "KNOWLEDGE_SEARCH_FAILED")

    def test_personal_answer_reports_unavailable_service_when_runtime_cannot_initialize(self) -> None:
        self.app.dependency_overrides.pop(get_user_knowledge_resources)

        with patch(
            "modules.knowledge.service.create_user_knowledge_resources",
            side_effect=ModuleNotFoundError("No module named 'langchain_chroma'"),
        ):
            response = self.client.post(
                "/api/user/qa/ask",
                headers=self.headers,
                json={"question": "What is in my library?", "document_ids": []},
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error_code"], "KNOWLEDGE_SERVICE_UNAVAILABLE")
        self.assertIn("知识服务尚未就绪", response.json()["message"])


if __name__ == "__main__":
    unittest.main()

"""Architecture checks that do not require FastAPI to be installed."""
import ast
from pathlib import Path
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8-sig")


class HttpArchitectureTests(unittest.TestCase):
    def test_main_is_only_an_entry_point(self) -> None:
        main_source = _source("main.py")
        self.assertIn("from api.http.application import create_app", main_source)
        self.assertIn("app = create_app()", main_source)
        self.assertNotIn("@app.", main_source)
        self.assertNotIn("add_routes(", main_source)
        self.assertNotIn("load_task_chain", main_source)

    def test_application_factory_owns_http_composition(self) -> None:
        source = _source("api/http/application.py")
        self.assertIn("class ApplicationOptions", source)
        self.assertIn("def create_app(", source)
        self.assertIn("app.state.database = database", source)
        self.assertIn("app.state.ai_configuration", source)
        self.assertIn("app.state.knowledge_resources_lock = threading.Lock()", source)
        self.assertIn("enable_langserve_routes", source)
        self.assertIn("_register_langserve_routes", source)
        self.assertIn("app.include_router(router)", source)
        for router_name in (
            "identity_router",
            "conversations_router",
            "documents_router",
            "knowledge_router",
            "planning_router",
            "task_execution_router",
            "task_automation_router",
        ):
            self.assertIn(router_name, source)

    def test_business_routes_live_in_routers(self) -> None:
        main_source = _source("main.py")
        route_sources = {
            "api/http/routers/identity.py": (
                "/api/auth/login", "/api/auth/refresh", "/api/user/password",
            ),
            "api/http/routers/task_execution.py": (
                "/api/goals", "/api/runs/{run_id}/steps/{step_id}/complete",
            ),
            "api/http/routers/task_automation.py": (
                "/api/triggers", "/api/triggers/{trigger_id}/fire",
            ),
            "api/http/routers/knowledge.py": (
                "/api/knowledge/search", "/api/vector/search",
            ),
            "api/http/routers/conversations.py": ('prefix="/api/chat"', "/groups", "/sessions"),
            "api/http/routers/documents.py": ("/api/user/documents/upload", "/api/user/qa/ask"),
            "api/http/routers/ai.py": ("/api/stream-chat", "/api/ai/image-caption"),
        }
        for path, routes in route_sources.items():
            source = _source(path)
            for route in routes:
                self.assertIn(route, source)
                self.assertNotIn(route, main_source)
        self.assertNotIn("/api/runs/{run_id}/commands", _source("api/http/routers/task_automation.py"))
        self.assertNotIn("reward_marketplace", _source("api/http/application.py"))
        self.assertFalse((BACKEND_ROOT / "api/http/routers/reward_marketplace.py").exists())

    def test_http_routes_do_not_depend_on_database_facade(self) -> None:
        router_directory = BACKEND_ROOT / "api" / "http" / "routers"
        for router_file in sorted(router_directory.glob("*.py")):
            source = router_file.read_text(encoding="utf-8-sig")
            self.assertNotIn("from database import Database", source, router_file.name)
            self.assertNotIn("Depends(get_db)", source, router_file.name)

    def test_legacy_planning_adapter_does_not_bypass_runtime_settings(self) -> None:
        source = _source("services/ai_services/advisor_chain.py")
        self.assertIn("get_chat_llm", source)
        self.assertNotIn("from config import config", source)
        self.assertNotIn("_pick_first_available_ollama_model", source)
        self.assertNotIn("ChatOllama", source)

    def test_legacy_qa_paths_are_not_exposed(self) -> None:
        application_source = _source("api/http/application.py")
        ai_router_source = _source("api/http/routers/ai.py")
        legacy_chain_source = _source("services/ai_services/qa_chain.py")
        self.assertNotIn("load_qa_chain", application_source)
        self.assertNotIn("/api/lc/qa", application_source)
        self.assertNotIn("from services.ai_services.qa_chain", ai_router_source)
        self.assertIn("HTTP_410_GONE", ai_router_source)
        self.assertIn("LegacyKnowledgePipelineRetired", legacy_chain_source)
        self.assertNotIn("get_embeddings", legacy_chain_source)

    def test_shared_knowledge_uses_the_unified_library_authorization_model(self) -> None:
        router_source = _source("api/http/routers/knowledge.py")
        library_router_source = _source("api/http/routers/library.py")
        repository_source = _source("adapters/sqlite/knowledge_document_repository.py")
        self.assertNotIn("/api/knowledge/system/search", router_source)
        self.assertNotIn("/api/knowledge/system/ask", router_source)
        self.assertIn("/api/library/ask", library_router_source)
        self.assertIn("include_global_shared", library_router_source)
        self.assertIn("active_library_catalog", repository_source)

    def test_system_knowledge_resources_are_application_owned(self) -> None:
        application_source = _source("api/http/application.py")
        dependency_source = _source("api/http/dependencies.py")
        router_source = _source("api/http/routers/knowledge_administration.py")
        store_source = _source("adapters/chroma/knowledge_store.py")
        shared_source = _source("modules/knowledge/shared_documents.py")
        self.assertIn("app.state.system_knowledge_resources = None", application_source)
        self.assertNotIn("system_knowledge_manager", application_source)
        self.assertIn("def get_system_knowledge_manager", dependency_source)
        self.assertIn("create_system_knowledge_resources(db, settings)", dependency_source)
        self.assertIn("get_system_knowledge_manager", router_source)
        self.assertNotIn("def _manager", router_source)
        self.assertIn('SYSTEM_COLLECTION = "system_knowledge"', store_source)
        self.assertIn("class SharedKnowledgeDocumentManager", shared_source)
        self.assertNotIn("asyncio.create_task", shared_source)

    def test_retired_knowledge_runtime_modules_are_absent(self) -> None:
        retired = [
            "api/user_vector_manager.py",
            "api/user_document_manager.py",
            "api/user_document_parser.py",
            "services/ai_services/rag_manager.py",
            "adapters/legacy/knowledge_adapters.py",
            "adapters/legacy/user_knowledge_maintenance.py",
        ]
        for relative_path in retired:
            self.assertFalse((BACKEND_ROOT / relative_path).exists(), relative_path)

    def test_authentication_dependency_requires_access_token_and_session(self) -> None:
        source = _source("api/http/dependencies.py")
        self.assertIn('decode_token(token, "access", settings)', source)
        self.assertIn('payload.get("ver", -1)', source)
        self.assertIn("repository.get_auth_session", source)
        self.assertIn('user["auth_session_id"]', source)
        self.assertIn("get_runtime_settings", source)
        self.assertIn("get_identity_repository", source)
        self.assertIn("SQLiteIdentityRepository", source)

    def test_request_logging_never_records_body_contents(self) -> None:
        source = _source("api/http/application.py")
        self.assertNotIn("await request.body()", source)
        self.assertNotIn("await request.json()", source)
        self.assertIn("request.url.path", source)
        self.assertIn('response.headers["X-Request-ID"]', source)

    def test_http_modules_are_syntax_valid(self) -> None:
        files = [
            BACKEND_ROOT / "main.py",
            BACKEND_ROOT / "errors.py",
            *sorted((BACKEND_ROOT / "api" / "http").rglob("*.py")),
        ]
        for file_path in files:
            ast.parse(file_path.read_text(encoding="utf-8-sig"), filename=str(file_path))


if __name__ == "__main__":
    unittest.main()

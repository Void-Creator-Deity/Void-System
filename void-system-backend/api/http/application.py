"""Application composition for the Void System HTTP API."""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
from dataclasses import dataclass
import logging
import time
import threading
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from adapters.sqlite.identity_repository import SQLiteIdentityRepository
from adapters.sqlite.plan_generation_repository import SQLitePlanGenerationRepository
from api.http.responses import APIResponse
from api.http.routers.administration import router as administration_router
from api.http.routers.ai import router as ai_router
from api.http.routers.analytics import router as analytics_router
from api.http.routers.conversations import router as conversations_router
from api.http.routers.documents import router as documents_router
from api.http.routers.growth import router as growth_router
from api.http.routers.identity import router as identity_router
from api.http.routers.knowledge import router as knowledge_router
from api.http.routers.library import router as library_router
from api.http.routers.knowledge_administration import router as knowledge_administration_router
from api.http.routers.planning import router as planning_router
from api.http.routers.personal_context import router as personal_context_router
from api.http.routers.session_files import router as session_files_router
from api.http.routers.system import router as system_router
from api.http.routers.task_automation import router as task_automation_router
from api.http.routers.task_execution import router as task_execution_router
from core.runtime_settings import RuntimeSettings
from database import Database
from errors import VoidSystemException
from middleware.auth import get_password_hash
from modules.administration.ai_configuration import AIConfigurationManager
from modules.growth.service import get_growth_profile
from modules.knowledge.jobs import KnowledgeJobWorker, get_knowledge_job_service
from modules.knowledge.service import create_user_knowledge_resources, migrate_private_knowledge_sources
from modules.personal_context.composition import compose_personal_context
from modules.planning.generation import (
    PlanGenerationWorker,
    generate_run_plan_draft,
    get_plan_generation_service,
)


logger = logging.getLogger("void-system")
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"


@dataclass(frozen=True)
class ApplicationOptions:
    """Runtime choices that make application composition explicit and testable."""

    database_path: Optional[str] = None
    enable_ai_routes: bool = True
    enable_langserve_routes: Optional[bool] = None
    bootstrap_admin: Optional[bool] = None
    enable_plan_generation_worker: bool = True
    enable_knowledge_job_worker: bool = True
    settings: Optional[RuntimeSettings] = None


def _error_response(
    request: Request,
    *,
    status_code: int,
    message: str,
    error_code: str,
    details: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=APIResponse(
            success=False,
            message=message,
            error_code=error_code,
            details=details,
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
        headers=headers,
    )


def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep validation responses useful without reflecting submitted credentials."""
    return [
        {
            "location": list(error.get("loc", ())),
            "message": error.get("msg", "请求数据无效"),
            "type": error.get("type", "validation_error"),
        }
        for error in errors
    ]


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(VoidSystemException)
    async def void_system_exception_handler(request: Request, exc: VoidSystemException) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details or None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="请求数据验证失败",
            error_code="VALIDATION_ERROR",
            details={"errors": _validation_details(exc.errors())},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message", "请求未能完成"))
            details: Optional[Any] = detail
        else:
            message = str(detail)
            details = None
        return _error_response(
            request,
            status_code=exc.status_code,
            message=message,
            error_code=f"HTTP_{exc.status_code}",
            details=details,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request failure")
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="系统内部错误",
            error_code="INTERNAL_SERVER_ERROR",
        )


def _register_request_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - started_at) * 1000
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        return response


def _register_langserve_routes(app: FastAPI) -> None:
    """Expose the optional legacy persona chain endpoint when explicitly enabled."""
    try:
        from langchain_core.runnables import RunnableLambda
        from langserve import add_routes        from services.ai_services.persona_chain import load_persona_chain

        def purge_internal_prompt(output: Any) -> Any:
            if isinstance(output, dict) and "content" in output:
                output = dict(output)
                output["content"] = str(output["content"]).strip()
                return output
            if hasattr(output, "content"):
                output.content = str(output.content).strip()
                return output
            return str(output).strip()

        for chain, path in ((load_persona_chain(), "/api/lc/persona"),):
            add_routes(app, chain | RunnableLambda(purge_internal_prompt), path=path)
        logger.warning("Legacy LangServe route is enabled for persona only")
    except Exception:
        logger.exception("LangServe routes could not be registered")
        raise


def create_app(options: Optional[ApplicationOptions] = None) -> FastAPI:
    """Create an independently startable HTTP application without model initialization."""
    options = options or ApplicationOptions()
    runtime_settings = options.settings or RuntimeSettings.from_environment()
    runtime_settings.validate_runtime()
    database_path = options.database_path or runtime_settings.get_database_path()
    enable_langserve_routes = (
        runtime_settings.ENABLE_LANGSERVE_ROUTES
        if options.enable_langserve_routes is None
        else options.enable_langserve_routes
    )
    bootstrap_admin = (
        runtime_settings.BOOTSTRAP_ADMIN_ENABLED
        if options.bootstrap_admin is None
        else options.bootstrap_admin
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        database: Optional[Database] = None
        try:
            database = Database(database_path)
            app.state.database = database
            try:
                source_migration = migrate_private_knowledge_sources(database, runtime_settings)
                if (
                    source_migration.get("preview_migrated_count", 0)
                    or source_migration["migrated_count"]
                    or source_migration["failed"]
                    or source_migration.get("preview_failures", [])
                ):
                    logger.info(
                        "Private knowledge encryption migration: previews=%s sources=%s already_secure=%s failures=%s",
                        source_migration.get("preview_migrated_count", 0), source_migration["migrated_count"],
                        source_migration["already_secure_count"],
                        len(source_migration["failed"]) + len(source_migration.get("preview_failures", [])),
                    )
            except Exception:
                # A source migration failure must not make the entire product
                # unavailable. The affected record stays versioned as legacy and
                # is retried on the next safe startup.
                logger.exception("Private knowledge source encryption migration could not complete")
            repository = SQLitePlanGenerationRepository(database.get_connection)
            interrupted_jobs = repository.recover_interrupted_jobs()
            if interrupted_jobs:
                logger.warning("Requeued or cancelled %s interrupted plan generation job(s) after restart", interrupted_jobs)
            knowledge_job_service = get_knowledge_job_service(database)
            interrupted_knowledge_jobs = knowledge_job_service.recover_interrupted_jobs()
            if interrupted_knowledge_jobs:
                logger.warning("Requeued or cancelled %s interrupted knowledge job(s) after restart", interrupted_knowledge_jobs)
            def publish_ai_runtime_settings(next_settings: RuntimeSettings) -> None:
                """Publish a complete AI settings snapshot and retire bound resources.

                Existing request dependencies retain their prior settings object.
                New dependency resolution sees this replacement and lazily rebuilds
                any vector or retrieval resource that was bound to the old profile.
                """
                app.state.runtime_settings = next_settings
                app.state.user_knowledge_resources = None
                app.state.user_knowledge_workspace = None
                app.state.system_knowledge_resources = None

            app.state.ai_configuration = AIConfigurationManager(
                _ENV_FILE,
                runtime_settings,
                runtime_update_callback=publish_ai_runtime_settings,
            )
            app.state.plan_generation_worker = None
            app.state.knowledge_job_worker = None
            app.state.user_knowledge_resources = None
            app.state.user_knowledge_workspace = None
            app.state.knowledge_resources_lock = threading.Lock()
            app.state.system_knowledge_resources = None
            app.state.system_knowledge_resources_lock = threading.Lock()
            if bootstrap_admin:
                required = (
                    runtime_settings.DEFAULT_ADMIN_USERNAME,
                    runtime_settings.DEFAULT_ADMIN_EMAIL,
                    runtime_settings.DEFAULT_ADMIN_PASSWORD,
                )
                if not all(required):
                    raise RuntimeError("BOOTSTRAP_ADMIN_ENABLED requires all DEFAULT_ADMIN_* values")
                database.ensure_default_admin(
                    username=runtime_settings.DEFAULT_ADMIN_USERNAME,
                    email=runtime_settings.DEFAULT_ADMIN_EMAIL,
                    password_hash=get_password_hash(runtime_settings.DEFAULT_ADMIN_PASSWORD),
                )
            if options.enable_plan_generation_worker:
                plan_generation_service = get_plan_generation_service(database)
                identity_repository = SQLiteIdentityRepository(database.get_connection)

                def execute_generation_job(job: dict[str, Any]) -> None:
                    def generate(job_snapshot: dict[str, Any], report: Callable[[str, int], bool]) -> dict[str, Any]:
                        user = identity_repository.get_user_by_id(str(job_snapshot["user_id"]))
                        if user is None or not user.get("is_active", True):
                            raise VoidSystemException(
                                "生成任务所属账号已不可用", "PLAN_GENERATION_USER_UNAVAILABLE", 409
                            )
                        current_settings = app.state.runtime_settings
                        return generate_run_plan_draft(
                            current_user=user,
                            profile=get_growth_profile(database),
                            companion=compose_personal_context(database, current_settings),
                            settings=current_settings,
                            topic=str(job_snapshot["topic"]),
                            execution_mode=str(job_snapshot["execution_mode"]),
                            max_steps=int(job_snapshot["max_steps"]),
                            advisor_prefs=dict(job_snapshot.get("advisor_prefs") or {}),
                            progress_callback=report,
                        )

                    plan_generation_service.execute_claimed(job, generate)

                worker = PlanGenerationWorker(plan_generation_service, execute_generation_job)
                worker.start()
                app.state.plan_generation_worker = worker
            if options.enable_knowledge_job_worker:
                def execute_knowledge_job(job: dict[str, Any]) -> None:
                    # Capture the active settings once for this worker-owned execution. A later
                    # administrator update affects newly claimed jobs but cannot mutate this job.
                    current_settings = app.state.runtime_settings
                    resources = create_user_knowledge_resources(database, current_settings)

                    def process(job_snapshot: dict[str, Any], report: Callable[[str, int], bool]) -> dict[str, Any]:
                        return asyncio.run(
                            resources.document_manager.process_stored_document(
                                str(job_snapshot["owner_id"]),
                                str(job_snapshot["document_id"]),
                                report_progress=report,
                            )
                        )

                    knowledge_job_service.execute_claimed(job, process)

                knowledge_worker = KnowledgeJobWorker(knowledge_job_service, execute_knowledge_job)
                knowledge_worker.start()
                app.state.knowledge_job_worker = knowledge_worker
                try:
                    encryption_resources = create_user_knowledge_resources(database, runtime_settings)
                    index_migration = encryption_resources.document_manager.queue_private_index_encryption_rebuilds()
                    if index_migration["queued_count"]:
                        logger.info(
                            "Queued %s private knowledge document(s) for encrypted Chroma rebuild",
                            index_migration["queued_count"],
                        )
                        knowledge_worker.wake()
                    if index_migration["failed"]:
                        logger.warning(
                            "Some private knowledge indexes await encrypted rebuild: %s",
                            len(index_migration["failed"]),
                        )
                except Exception:
                    # Retrieval infrastructure is intentionally optional at boot.
                    # The source migration above has already protected originals;
                    # the encrypted vector migration retries when the service is
                    # next started with a working embedding configuration.
                    logger.exception("Private knowledge encrypted index rebuild could not be queued")
            yield
        finally:
            app.state.user_knowledge_resources = None
            app.state.user_knowledge_workspace = None
            app.state.system_knowledge_resources = None
            worker = getattr(app.state, "plan_generation_worker", None)
            if worker is not None:
                worker.stop()
            app.state.plan_generation_worker = None
            knowledge_worker = getattr(app.state, "knowledge_job_worker", None)
            if knowledge_worker is not None:
                knowledge_worker.stop()
            app.state.knowledge_job_worker = None
            app.state.ai_configuration = None
            app.state.database = None
            if database is not None:
                database.close()

    app = FastAPI(
        title="Void System Core API",
        description="个人成长工作空间的模块化后端 API",
        version="0.3.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.runtime_settings = runtime_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    _register_request_middleware(app)
    _register_error_handlers(app)

    for router in (
        administration_router,
        analytics_router,
        identity_router,
        conversations_router,
        documents_router,
        growth_router,
        knowledge_administration_router,
        session_files_router,
        system_router,
        task_execution_router,
        task_automation_router,
        knowledge_router,
        library_router,
        planning_router,
        personal_context_router,
    ):
        app.include_router(router)
    if options.enable_ai_routes:
        app.include_router(ai_router)
    if enable_langserve_routes:
        _register_langserve_routes(app)
    return app

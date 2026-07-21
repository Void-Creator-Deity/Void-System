"""FastAPI dependencies shared by Growth App routers."""
import logging
from typing import Any, Dict, Optional

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from adapters.sqlite.identity_repository import SQLiteIdentityRepository
from core.identity_contracts import IdentityRepository
from core.runtime_settings import RuntimeSettings
from database import Database
from errors import ErrorCode, VoidSystemException
from middleware.auth import decode_token


logger = logging.getLogger("void-system.dependencies")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


def get_db(request: Request) -> Database:
    """Return the application-owned database adapter."""
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise VoidSystemException.from_error_code(
            ErrorCode.SYSTEM_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return database


def get_runtime_settings(request: Request) -> RuntimeSettings:
    """Return the settings instance owned by this FastAPI application."""
    settings = getattr(request.app.state, "runtime_settings", None)
    if settings is None:
        raise VoidSystemException.from_error_code(
            ErrorCode.SYSTEM_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return settings


def get_identity_repository(
    db: Database = Depends(get_db),
) -> IdentityRepository:
    return SQLiteIdentityRepository(db.get_connection)


def get_user_service(
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    from services.user_service import UserService

    return UserService(repository, settings)





def get_session_attachments(
    db: Database = Depends(get_db),
):
    """Provide temporary attachment operations behind their legacy adapter."""
    from adapters.legacy.session_attachment_gateway import LegacySessionAttachmentGateway
    from modules.session_attachments.service import SessionAttachments

    return SessionAttachments(LegacySessionAttachmentGateway(db))

def get_growth_profile(
    db: Database = Depends(get_db),
):
    """Provide the Growth Profile module using the application database."""
    from modules.growth.service import get_growth_profile as compose_growth_profile

    return compose_growth_profile(db)

def get_analytics_repository(
    db: Database = Depends(get_db),
):
    """Provide the administrator analytics repository."""
    from adapters.sqlite.analytics_repository import SQLiteAnalyticsRepository

    return SQLiteAnalyticsRepository(db.get_connection)


def get_user_library_catalog(
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Provide the caller-neutral unified library catalogue.

    Inputs: the application-owned database and runtime encryption settings.
    Output: a repository that reads private documents and shared catalogue
    references without materializing copies. Called by the user library HTTP API.
    """
    from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
    from modules.knowledge.encrypted_storage import KnowledgeSourceCipher

    return SQLiteKnowledgeDocumentRepository(
        db.get_connection,
        cipher=KnowledgeSourceCipher(settings, settings.BASE_DIR / "user_documents"),
    )


def get_system_knowledge_catalog(
    db: Database = Depends(get_db),
):
    """Provide the system knowledge catalog read model."""
    from modules.knowledge.admin import SystemKnowledgeCatalog
    from adapters.sqlite.system_knowledge_repository import SQLiteSystemKnowledgeRepository

    return SystemKnowledgeCatalog(SQLiteSystemKnowledgeRepository(db.get_connection))


def get_system_health(
    db: Database = Depends(get_db),
):
    """Provide infrastructure health checks without exposing Database to routes."""
    from modules.system.health import SystemHealth

    return SystemHealth(db.test_connection)

def get_analytics_dashboard(
    db: Database = Depends(get_db),
):
    """Provide the user analytics read-model."""
    from modules.analytics.service import get_analytics_dashboard as compose_analytics_dashboard

    return compose_analytics_dashboard(db)

def get_plan_generation_service(
    db: Database = Depends(get_db),
):
    """Provide durable AI plan generation jobs backed by the application database."""
    from modules.planning.generation import (
        get_plan_generation_service as compose_plan_generation_service,
    )

    return compose_plan_generation_service(db)


def get_knowledge_job_service(
    db: Database = Depends(get_db),
):
    """Provide owner-scoped durable knowledge processing jobs."""
    from modules.knowledge.jobs import get_knowledge_job_service as compose_knowledge_job_service

    return compose_knowledge_job_service(db)


def get_plan_draft_service(
    db: Database = Depends(get_db),
):
    """Provide persisted Plan Draft editing and atomic publication use cases."""
    from modules.planning.drafts import get_plan_draft_service as compose_plan_draft_service

    return compose_plan_draft_service(db)


def get_task_automation(
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Provide Trigger-to-Run automation and durable Run commands."""
    from modules.tasks.service import get_task_automation as compose_task_automation

    return compose_task_automation(db, settings)


def get_task_execution(
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Provide durable Goal and Run execution."""
    from modules.tasks.service import get_task_execution as compose_task_execution

    return compose_task_execution(db, settings)


def get_conversation_service(
    db: Database = Depends(get_db),
):
    """Provide conversation lifecycle operations without leaking Database to routes."""
    from modules.conversations.service import get_conversation_service as compose_conversation_service

    return compose_conversation_service(db)


def _resolve_user(
    token: str,
    repository: IdentityRepository,
    settings: RuntimeSettings,
) -> Optional[Dict[str, Any]]:
    try:
        payload = decode_token(token, "access", settings)
    except VoidSystemException:
        return None

    user = repository.get_user_by_id(str(payload["sub"]))
    if user is None or not user.get("is_active", True):
        return None
    if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        return None
    session_id = str(payload["sid"])
    session = repository.get_auth_session(session_id, user["user_id"])
    if session is None or session.get("revoked_at"):
        return None
    user["auth_session_id"] = session_id
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> Dict[str, Any]:
    user = _resolve_user(token, repository, settings)
    if user is None:
        raise VoidSystemException(
            message="认证凭据无效或用户不存在",
            error_code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.get("is_active", True):
        raise VoidSystemException.from_error_code(ErrorCode.USER_INACTIVE)
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    user = _resolve_user(token, repository, settings)
    if user is None:
        raise VoidSystemException(
            message="Authentication credentials are invalid or expired",
            error_code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.get("is_active", True):
        raise VoidSystemException.from_error_code(ErrorCode.USER_INACTIVE)
    return user


async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if current_user.get("role", "user") != "admin":
        raise VoidSystemException(
            message="需要管理员权限",
            error_code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


def get_system_knowledge_resources(
    request: Request,
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Lazily compose shared knowledge through the unified store and engine."""
    resources = getattr(request.app.state, "system_knowledge_resources", None)
    if resources is not None:
        return resources
    lock = getattr(request.app.state, "system_knowledge_resources_lock", None)
    if lock is None:
        from threading import Lock
        lock = Lock()
        request.app.state.system_knowledge_resources_lock = lock
    with lock:
        resources = getattr(request.app.state, "system_knowledge_resources", None)
        if resources is None:
            try:
                from modules.knowledge.service import create_system_knowledge_resources
                resources = create_system_knowledge_resources(db, settings)
            except VoidSystemException:
                raise
            except Exception as exc:
                _raise_knowledge_service_unavailable("共享", exc)
            request.app.state.system_knowledge_resources = resources
    return resources


def get_system_knowledge_manager(
    resources: Any = Depends(get_system_knowledge_resources),
):
    """Expose shared catalog operations from the unified knowledge composition."""
    return resources.manager

def get_user_knowledge_resources(
    request: Request,
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Lazily create Knowledge resources over the application database."""
    resources = getattr(request.app.state, "user_knowledge_resources", None)
    if resources is not None:
        return resources

    lock = getattr(request.app.state, "knowledge_resources_lock", None)
    if lock is None:
        from threading import Lock

        lock = Lock()
        request.app.state.knowledge_resources_lock = lock

    with lock:
        resources = getattr(request.app.state, "user_knowledge_resources", None)
        if resources is None:
            try:
                from modules.knowledge.service import create_user_knowledge_resources

                resources = create_user_knowledge_resources(db, settings)
            except VoidSystemException:
                raise
            except Exception as exc:
                _raise_knowledge_service_unavailable("个人", exc)
            request.app.state.user_knowledge_resources = resources
    return resources


def _raise_knowledge_service_unavailable(scope: str, exc: Exception) -> None:
    """Convert runtime initialization failures into a stable knowledge-service response."""
    logger.exception("%s knowledge service initialization failed", scope, exc_info=exc)
    raise VoidSystemException(
        message=f"{scope}知识服务尚未就绪，请检查知识库运行依赖和嵌入服务后重试。",
        error_code="KNOWLEDGE_SERVICE_UNAVAILABLE",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    ) from exc


def get_user_knowledge_workspace(
    request: Request,
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Compose document metadata workflows without loading retrieval adapters."""
    workspace = getattr(request.app.state, "user_knowledge_workspace", None)
    if workspace is not None:
        return workspace

    resources = getattr(request.app.state, "user_knowledge_resources", None)
    if resources is not None:
        return resources.workspace

    lock = getattr(request.app.state, "user_knowledge_workspace_lock", None)
    if lock is None:
        from threading import Lock

        lock = Lock()
        request.app.state.user_knowledge_workspace_lock = lock

    with lock:
        workspace = getattr(request.app.state, "user_knowledge_workspace", None)
        if workspace is None:
            from modules.knowledge.service import create_user_knowledge_workspace

            workspace = create_user_knowledge_workspace(db, settings)
            request.app.state.user_knowledge_workspace = workspace
    return workspace


def get_personal_context(
    db: Database = Depends(get_db),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Compose Personal Context through the shared request/worker composition helper."""
    from modules.personal_context.composition import compose_personal_context

    return compose_personal_context(db, settings)

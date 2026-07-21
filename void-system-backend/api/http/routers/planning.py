"""HTTP adapter for durable Planning Engine jobs and reviewable Plan Drafts."""
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, status

from api.http.dependencies import (
    get_current_user,
    get_plan_generation_service,
    get_plan_draft_service,
)
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.planning import (
    PlanDraftPublishRequest,
    PlanDraftUpdateRequest,
    RunPlanRequest,
)
from modules.planning.drafts import PlanDraftService
from modules.planning.generation import PlanGenerationService

router = APIRouter(tags=["AI服务"])


@router.post(
    "/api/plan-generations",
    summary="Start a durable execution-plan generation job",
    response_model=APIResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_run_plan_generation(
    body: RunPlanRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanGenerationService = Depends(get_plan_generation_service),
) -> APIResponse:
    """Store a generation request and wake the application-owned durable worker.

    The request only creates a database job. It never performs model work through FastAPI
    BackgroundTasks, so browser disconnects and request completion cannot own execution.
    """
    job = service.create(current_user["user_id"], body.model_dump())
    worker = getattr(request.app.state, "plan_generation_worker", None)
    if worker is not None:
        worker.wake()
    return create_success_response(
        "Plan generation started. You can leave this page and return to the result.",
        _serialize_generation_job(job),
    )

@router.get(
    "/api/plan-generations",
    summary="Restore recent durable execution-plan generation jobs",
    response_model=APIResponse,
)
async def list_run_plan_generations(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanGenerationService = Depends(get_plan_generation_service),
) -> APIResponse:
    """Return persisted jobs so a refreshed page can restore its background work."""
    return create_success_response(
        "Plan generation history loaded",
        {"items": [_serialize_generation_job(job) for job in service.list_recent(current_user["user_id"])]},
    )


@router.get(
    "/api/plan-generations/{generation_id}",
    summary="Read a durable execution-plan generation job",
    response_model=APIResponse,
)
async def get_run_plan_generation(
    generation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanGenerationService = Depends(get_plan_generation_service),
) -> APIResponse:
    return create_success_response(
        "Plan generation status loaded",
        _serialize_generation_job(service.get(current_user["user_id"], generation_id)),
    )


@router.delete(
    "/api/plan-generations/{generation_id}",
    summary="Stop waiting for a durable execution-plan generation job",
    response_model=APIResponse,
)
async def cancel_run_plan_generation(
    generation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanGenerationService = Depends(get_plan_generation_service),
) -> APIResponse:
    return create_success_response(
        "Plan generation will no longer be used",
        _serialize_generation_job(service.cancel(current_user["user_id"], generation_id)),
    )


def _serialize_generation_job(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generation_id": job["generation_id"],
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
        "topic": job["topic"],
        "execution_mode": job["execution_mode"],
        "max_steps": job["max_steps"],
        "result": job.get("result"),
        "draft_id": job.get("draft_id"),
        "error_message": job.get("error_message"),
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "attempt_count": int(job.get("attempt_count") or 0),
        "cancel_requested": bool(job.get("cancel_requested", False)),
    }


@router.get(
    "/api/plan-drafts",
    summary="恢复近期可审阅方案草稿",
    response_model=APIResponse,
)
async def list_plan_drafts(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanDraftService = Depends(get_plan_draft_service),
) -> APIResponse:
    """List persisted Plan Drafts for cross-page and post-refresh recovery."""
    return create_success_response(
        "方案草稿已加载",
        {"items": [_serialize_plan_draft(item) for item in service.list_recent(current_user["user_id"])]},
    )


@router.get(
    "/api/plan-drafts/{draft_id}",
    summary="读取可审阅方案草稿",
    response_model=APIResponse,
)
async def get_plan_draft(
    draft_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanDraftService = Depends(get_plan_draft_service),
) -> APIResponse:
    """Return one owner-scoped draft including its authoritative editable payload."""
    return create_success_response("方案草稿已加载", _serialize_plan_draft(service.get(current_user["user_id"], draft_id)))


@router.patch(
    "/api/plan-drafts/{draft_id}",
    summary="保存方案草稿修改",
    response_model=APIResponse,
)
async def update_plan_draft(
    draft_id: str,
    body: PlanDraftUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanDraftService = Depends(get_plan_draft_service),
) -> APIResponse:
    """Save a fully validated editable plan only when the rendered draft version is current."""
    draft = service.update(current_user["user_id"], draft_id, body.payload, body.expected_version)
    return create_success_response("方案修改已保存", _serialize_plan_draft(draft))


@router.post(
    "/api/plan-drafts/{draft_id}/publish",
    summary="将方案草稿原子发布为目标和行动",
    response_model=APIResponse,
)
async def publish_plan_draft(
    draft_id: str,
    body: PlanDraftPublishRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PlanDraftService = Depends(get_plan_draft_service),
) -> APIResponse:
    """Publish one draft once; repeated browser retries resolve to the same Goal and Run."""
    draft = service.publish(current_user["user_id"], draft_id, body.idempotency_key.strip())
    return create_success_response("方案已开始推进", _serialize_plan_draft(draft))


def _serialize_plan_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    """Map a database draft to the public owner-scoped plan review contract.

    Inputs:
        draft: Internal Plan Draft snapshot returned by PlanDraftService.
    Outputs:
        Editable payload, optimistic version, publication status, and public Goal/Run references.
    Called by:
        Plan Draft list/read/update/publish planning routes and first-party plans client.
    Side effects:
        None; lease tokens, raw worker data, and other users' records are never accepted here.
    Failure:
        Missing mandatory identifiers is a programmer error and surfaces during endpoint tests.
    Invariants:
        The payload remains the server authority; publication identifiers appear only after atomic publish.
    """
    return {
        "draft_id": draft["draft_id"],
        "generation_id": draft.get("generation_id"),
        "status": draft["status"],
        "version": int(draft.get("version") or 1),
        "payload": draft.get("payload") or {},
        "published_goal_id": draft.get("published_goal_id"),
        "published_run_id": draft.get("published_run_id"),
        "created_at": draft["created_at"],
        "updated_at": draft["updated_at"],
        "published_at": draft.get("published_at"),
    }

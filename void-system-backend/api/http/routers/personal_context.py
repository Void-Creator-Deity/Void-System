"""HTTP adapter for permissioned personal context and system companion workflows."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_current_user, get_personal_context
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.personal_context import (
    CompanionSettingsUpdate,
    MemoryCreate,
    MemoryReview,
    MemoryUpdate,
    ProfileHypothesisInferenceRequest,
    ProfileHypothesisReview,
)
from core.personal_context_contracts import PersonalContextError
from errors import VoidSystemException
from modules.personal_context.service import PersonalContext


router = APIRouter(prefix="/api/companion", tags=["Companion"])


def _translate_error(exc: PersonalContextError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.get("/settings", summary="Get companion settings", response_model=APIResponse)
async def get_companion_settings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    return create_success_response(
        "Companion settings loaded",
        data={"settings": companion.get_settings(current_user["user_id"])},
    )


@router.put("/settings", summary="Update companion settings", response_model=APIResponse)
async def update_companion_settings(
    payload: CompanionSettingsUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        settings = companion.update_settings(
            current_user["user_id"], payload.model_dump(exclude_unset=True)
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Companion settings updated", data={"settings": settings})


@router.get("/context", summary="Build an explainable personal context", response_model=APIResponse)
async def get_companion_context(
    purpose: str = Query("companion_context", min_length=1, max_length=80),
    sections: Optional[List[str]] = Query(None),
    item_budget: int = Query(24, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        snapshot = companion.build_context(
            current_user["user_id"],
            current_user,
            purpose=purpose,
            requested_sections=sections,
            item_budget=item_budget,
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal context built", data={"context": snapshot})


@router.get("/briefing", summary="Get the current companion briefing", response_model=APIResponse)
async def get_companion_briefing(
    item_budget: int = Query(24, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        briefing = companion.build_briefing(
            current_user["user_id"], current_user, item_budget=item_budget
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Companion briefing loaded", data={"briefing": briefing})


@router.get("/profile", summary="Get explainable effective profile", response_model=APIResponse)
async def get_profile_view(
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        profile = companion.get_profile_view(current_user["user_id"])
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Profile cognition loaded", data={"profile": profile})


@router.post(
    "/profile/hypotheses/infer",
    summary="Organize consented profile signals into reviewable hypotheses",
    response_model=APIResponse,
)
async def infer_profile_hypotheses(
    payload: ProfileHypothesisInferenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        result = companion.infer_profile_hypotheses(
            current_user["user_id"],
            max_signals=payload.max_signals,
            max_hypotheses=payload.max_hypotheses,
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        "Profile hypotheses are ready for your review", data=result
    )


@router.patch(
    "/profile/hypotheses/{hypothesis_id}/review",
    summary="Confirm, correct, or decline a profile hypothesis",
    response_model=APIResponse,
)
async def review_profile_hypothesis(
    hypothesis_id: str,
    payload: ProfileHypothesisReview,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        hypothesis = companion.review_profile_hypothesis(
            current_user["user_id"], hypothesis_id, payload.model_dump()
        )
        profile = companion.get_profile_view(current_user["user_id"])
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        "Profile hypothesis reviewed", data={"hypothesis": hypothesis, "profile": profile}
    )


@router.get("/memories", summary="List personal memories", response_model=APIResponse)
async def list_memories(
    memory_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        memories = companion.list_memories(
            current_user["user_id"],
            memory_type=memory_type,
            status=status,
            review_status=review_status,
            limit=limit,
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memories loaded", data={"memories": memories})


@router.get(
    "/memories/suggestions",
    summary="List reviewable personal memory suggestions",
    response_model=APIResponse,
)
async def list_memory_suggestions(
    limit: int = Query(100, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    return create_success_response(
        "Personal memory suggestions loaded",
        data={"suggestions": companion.list_memory_suggestions(current_user["user_id"], limit=limit)},
    )


@router.post("/memories", summary="Create a personal memory", response_model=APIResponse)
async def create_memory(
    payload: MemoryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        memory = companion.create_memory(current_user["user_id"], payload.model_dump())
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memory created", data={"memory": memory})


@router.patch(
    "/memories/{memory_id}/review",
    summary="Confirm, correct, or reject a memory suggestion",
    response_model=APIResponse,
)
async def review_memory(
    memory_id: str,
    payload: MemoryReview,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        memory = companion.review_memory(
            current_user["user_id"], memory_id, payload.model_dump(exclude_unset=True)
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memory reviewed", data={"memory": memory})


@router.patch("/memories/{memory_id}", summary="Update a personal memory", response_model=APIResponse)
async def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        memory = companion.update_memory(
            current_user["user_id"], memory_id, payload.model_dump(exclude_unset=True)
        )
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memory updated", data={"memory": memory})


@router.delete("/memories/{memory_id}", summary="Delete a personal memory", response_model=APIResponse)
async def delete_memory(
    memory_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        companion.delete_memory(current_user["user_id"], memory_id)
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memory archived")


@router.delete(
    "/memories/{memory_id}/purge",
    summary="Permanently remove an archived personal memory",
    response_model=APIResponse,
)
async def purge_memory(
    memory_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    try:
        companion.purge_memory(current_user["user_id"], memory_id)
    except PersonalContextError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Personal memory permanently removed")


@router.get("/access-log", summary="List personal context access records", response_model=APIResponse)
async def list_context_access_log(
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    companion: PersonalContext = Depends(get_personal_context),
) -> APIResponse:
    records = companion.access_log(current_user["user_id"], limit)
    return create_success_response("Context access log loaded", data={"records": records})

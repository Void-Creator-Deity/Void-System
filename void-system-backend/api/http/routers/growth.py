"""HTTP adapter for a user's growth profile and durable points activity."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_current_user, get_growth_profile
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.growth import AttributeCreate, AttributeUpdate
from core.growth_contracts import GrowthProfileError
from errors import VoidSystemException
from modules.growth.profile import GrowthProfile


logger = logging.getLogger("void-system.growth")
router = APIRouter(tags=["Growth"])


def _translate_error(exc: GrowthProfileError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.get("/api/growth/points/balance", summary="Get growth-point balance", response_model=APIResponse)
async def get_growth_points_balance(
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    return create_success_response(
        "Growth points loaded", data={"growth_points": profile.balance(current_user["user_id"])}
    )


@router.get("/api/growth/points/activity", summary="Get growth-point activity", response_model=APIResponse)
async def get_growth_point_activity(
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    return create_success_response(
        "Growth-point activity loaded",
        data={"history": profile.growth_point_activity(current_user["user_id"], limit)},
    )


@router.get("/api/growth/points/summary", summary="Get growth-point summary", response_model=APIResponse)
async def get_growth_points_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    return create_success_response(
        "Growth-point summary loaded", data=profile.growth_point_summary(current_user["user_id"])
    )


@router.get("/api/attributes", summary="List growth attributes", response_model=APIResponse)
async def list_growth_attributes(
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    attributes = profile.list_capabilities(current_user["user_id"])
    logger.debug("Growth attributes loaded: user_id=%s count=%s", current_user["user_id"], len(attributes))
    return create_success_response("Growth attributes loaded", data=attributes)


@router.post("/api/attributes", summary="Create growth attribute", response_model=APIResponse)
async def create_growth_attribute(
    attribute_data: AttributeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    try:
        attribute = profile.create_capability(current_user["user_id"], attribute_data.model_dump())
    except GrowthProfileError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Growth attribute created", data=attribute)


@router.put("/api/attributes/{attr_id}", summary="Update growth attribute", response_model=APIResponse)
async def update_growth_attribute(
    attr_id: str,
    attribute_data: AttributeUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    try:
        attribute = profile.update_capability(
            current_user["user_id"], attr_id, attribute_data.model_dump(exclude_unset=True)
        )
    except GrowthProfileError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Growth attribute updated", data=attribute)


@router.delete("/api/attributes/{attr_id}", summary="Delete growth attribute", response_model=APIResponse)
async def delete_growth_attribute(
    attr_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
) -> APIResponse:
    try:
        profile.delete_capability(current_user["user_id"], attr_id)
    except GrowthProfileError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Growth attribute deleted")

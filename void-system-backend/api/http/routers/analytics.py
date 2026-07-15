"""HTTP adapter for user insights and administrator analytics."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, status as http_status

from api.http.dependencies import get_analytics_dashboard, get_analytics_repository, get_current_admin, get_current_user
from core.analytics_contracts import AnalyticsRepository
from api.http.responses import APIResponse, create_success_response
from errors import VoidSystemException
from modules.analytics.dashboard import AnalyticsDashboard


logger = logging.getLogger("void-system.analytics")
router = APIRouter(tags=["Analytics"])


@router.get("/api/stats/overview", summary="Get the user's dashboard overview", response_model=APIResponse)
async def get_stats_overview(
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard: AnalyticsDashboard = Depends(get_analytics_dashboard),
) -> APIResponse:
    return create_success_response(
        "Dashboard overview loaded",
        data={**dashboard.overview(current_user["user_id"]), "timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get("/api/admin/visualization/overview", summary="Get administrator analytics overview", response_model=APIResponse)
async def get_visualization_overview(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "Analytics overview loaded",
            data={
                "user_stats": repository.global_user_stats(),
                "task_stats": repository.global_task_stats(),
                "attribute_stats": repository.global_attribute_stats(),
                "economy_stats": repository.global_economy_stats(),
                "document_stats": repository.global_document_stats(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Analytics overview failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Analytics overview could not be loaded",
            error_code="VISUALIZATION_OVERVIEW_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/visualization/users", summary="Get user analytics", response_model=APIResponse)
async def get_users_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "User analytics loaded",
            data={
                "registration_trend": repository.user_registration_trend(days),
                "activity_stats": repository.user_activity_stats(days),
                "level_distribution": repository.user_level_distribution(),
                "period_days": days,
            },
        )
    except Exception as exc:
        logger.error("User analytics failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="User analytics could not be loaded",
            error_code="USER_VISUALIZATION_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/visualization/tasks", summary="Get task analytics", response_model=APIResponse)
async def get_tasks_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "Task analytics loaded",
            data={
                "status_distribution": repository.task_status_distribution(),
                "completion_trend": repository.task_completion_trend(days),
                "category_stats": repository.task_category_stats(),
                "duration_stats": repository.task_duration_stats(),
                "period_days": days,
            },
        )
    except Exception as exc:
        logger.error("Task analytics failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Task analytics could not be loaded",
            error_code="TASK_VISUALIZATION_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/visualization/attributes", summary="Get attribute analytics", response_model=APIResponse)
async def get_attributes_visualization(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "Attribute analytics loaded",
            data={
                "type_distribution": repository.attribute_type_distribution(),
                "value_distribution": repository.attribute_value_distribution(),
                "popular_attributes": repository.popular_attributes(limit=10),
            },
        )
    except Exception as exc:
        logger.error("Attribute analytics failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Attribute analytics could not be loaded",
            error_code="ATTRIBUTE_VISUALIZATION_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/visualization/economy", summary="Get economy analytics", response_model=APIResponse)
async def get_economy_visualization(
    days: int = Query(30, ge=1, le=365),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "Economy analytics loaded",
            data={
                "transaction_trend": repository.coin_transaction_trend(days),
                "balance_distribution": repository.user_balance_distribution(),
                "item_sales_stats": repository.item_sales_stats(),
                "health_metrics": repository.economy_health_metrics(),
                "period_days": days,
            },
        )
    except Exception as exc:
        logger.error("Economy analytics failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Economy analytics could not be loaded",
            error_code="ECONOMY_VISUALIZATION_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

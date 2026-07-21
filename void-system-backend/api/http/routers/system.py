"""HTTP adapter for system status and API discovery."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from api.http.dependencies import get_system_health
from api.http.responses import APIResponse, create_success_response
from modules.system.health import SystemHealth


logger = logging.getLogger("void-system.system")
router = APIRouter(tags=["System"])
_API_VERSION = "0.3.0"


@router.get("/", summary="System status", response_model=APIResponse)
async def read_root() -> APIResponse:
    """Return a compact status payload for the workspace core."""
    return create_success_response(
        "System is running",
        data={
            "system": "VOID CORE ACTIVE",
            "status": "running",
            "version": _API_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/api/health", summary="Health check", response_model=APIResponse)
async def health_check(health: SystemHealth = Depends(get_system_health)) -> APIResponse | JSONResponse:
    """Return service health and database connectivity without masking dependency failures."""
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        health_data = health.inspect()
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=APIResponse(
                success=False,
                message="Database health check failed",
                data={
                    "status": "unhealthy",
                    "timestamp": timestamp,
                    "database": "unhealthy",
                    "schema": "incompatible_or_unavailable",
                    "version": _API_VERSION,
                },
                error_code="DATABASE_UNAVAILABLE",
            ).model_dump(),
        )

    return create_success_response(
        "System health loaded",
        data={
            "status": "healthy",
            "timestamp": timestamp,
            **health_data,
            "version": _API_VERSION,
        },
    )


def _iter_registered_routes(route_items: Any):
    """Yield concrete routes from both eager and lazy FastAPI router includes."""
    for route in route_items:
        included_router = getattr(route, "original_router", None)
        if included_router is not None:
            yield from _iter_registered_routes(getattr(included_router, "routes", []))
            continue
        if hasattr(route, "path"):
            yield route


@router.get("/api/routes", summary="List API routes", response_model=APIResponse)
async def list_routes(request: Request) -> APIResponse:
    """Return registered endpoints, including FastAPI's lazy included routers."""
    routes: List[Dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for route in _iter_registered_routes(request.app.routes):
        methods = tuple(sorted(getattr(route, "methods", ["GET"])))
        route_data = {
            "path": route.path,
            "methods": list(methods),
            "name": getattr(route, "name", ""),
            "summary": getattr(route, "summary", ""),
        }
        identity = (route_data["path"], methods, route_data["name"])
        if identity not in seen:
            routes.append(route_data)
            seen.add(identity)

    return create_success_response("API routes loaded", data={"routes": routes})

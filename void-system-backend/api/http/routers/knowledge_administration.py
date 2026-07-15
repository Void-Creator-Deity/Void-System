"""HTTP adapter for system Knowledge Administration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile, status as http_status

from api.http.dependencies import (
    get_current_admin,
    get_system_knowledge_catalog,
    get_system_knowledge_manager,
)
from api.http.responses import APIResponse, create_success_response
from errors import VoidSystemException
from modules.knowledge.admin import SystemKnowledgeCatalog


logger = logging.getLogger("void-system.knowledge-admin")
router = APIRouter(tags=["Knowledge Administration"])



def _parse_tags(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None or raw.strip() == "":
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def _raise_knowledge_failure(
    result: Dict[str, Any],
    *,
    default_code: str,
    default_message: str,
) -> None:
    status_code = int(result.get("status_code", http_status.HTTP_503_SERVICE_UNAVAILABLE))
    message = str(result.get("message") or default_message)
    if status_code >= http_status.HTTP_500_INTERNAL_SERVER_ERROR:
        message = default_message
    raise VoidSystemException(
        message=message,
        error_code=str(result.get("error_code") or default_code),
        status_code=status_code,
    )


@router.get("/api/admin/rag/documents", summary="List system knowledge documents", response_model=APIResponse)
async def list_system_knowledge_documents(
    tags: Optional[str] = None,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    del current_admin
    try:
        result = manager.list_documents(_parse_tags(tags))
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_LIST_FAILED",
                default_message="Knowledge documents are temporarily unavailable",
            )
        return create_success_response(
            result.get("message", "Knowledge documents loaded"),
            data={
                "documents": result.get("documents", []),
                "count": result.get("count", 0),
            },
        )
    except Exception as exc:
        logger.error("System knowledge document listing failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge documents could not be loaded",
            error_code="RAG_LIST_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/rag/tags", summary="List system knowledge tags", response_model=APIResponse)
async def get_system_knowledge_tags(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    catalog: SystemKnowledgeCatalog = Depends(get_system_knowledge_catalog),
) -> APIResponse:
    del current_admin
    try:
        return create_success_response(
            "Knowledge tags loaded",
            data={"tags": catalog.tags()},
        )
    except Exception as exc:
        logger.error("System knowledge tags failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge tags could not be loaded",
            error_code="RAG_TAGS_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.post("/api/admin/rag/documents", summary="Add a system knowledge document", response_model=APIResponse)
async def upload_system_knowledge_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    try:
        file_name = file.filename or "knowledge-document"
        result = manager.add_document_async(
            file_data=await file.read(),
            metadata={
                "title": title.strip() if title else file_name,
                "file_name": file_name,
                "uploaded_by": current_admin["user_id"],
                "tags": _parse_tags(tags) or [],
                "description": description or "",
            },
        )
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_UPLOAD_FAILED",
                default_message="Knowledge document could not be added",
            )
        return create_success_response(
            result.get("message", "Knowledge document added"),
            data={"doc_id": result.get("doc_id")},
        )
    except Exception as exc:
        logger.error("System knowledge upload failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge document could not be added",
            error_code="RAG_UPLOAD_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/api/admin/rag/documents/{doc_id}", summary="Get a system knowledge document", response_model=APIResponse)
async def get_system_knowledge_document(
    doc_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    del current_admin
    try:
        result = manager.get_document(doc_id)
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_GET_FAILED",
                default_message="Knowledge document is temporarily unavailable",
            )
        return create_success_response(
            result.get("message", "Knowledge document loaded"),
            data={"document": result.get("document")},
        )
    except Exception as exc:
        logger.error("System knowledge detail failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge document could not be loaded",
            error_code="RAG_GET_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.put("/api/admin/rag/documents/{doc_id}", summary="Update a system knowledge document", response_model=APIResponse)
async def update_system_knowledge_document(
    doc_id: str,
    updates: Dict[str, Any] = Body(...),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    del current_admin
    try:
        result = manager.update_document(doc_id, updates)
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_UPDATE_FAILED",
                default_message="Knowledge document could not be updated",
            )
        return create_success_response(result.get("message", "Knowledge document updated"))
    except Exception as exc:
        logger.error("System knowledge update failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge document could not be updated",
            error_code="RAG_UPDATE_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.delete("/api/admin/rag/documents/{doc_id}", summary="Delete a system knowledge document", response_model=APIResponse)
async def delete_system_knowledge_document(
    doc_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    del current_admin
    try:
        result = manager.delete_document(doc_id)
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_DELETE_FAILED",
                default_message="Knowledge document could not be deleted",
            )
        return create_success_response(result.get("message", "Knowledge document deleted"))
    except Exception as exc:
        logger.error("System knowledge delete failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge document could not be deleted",
            error_code="RAG_DELETE_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.post("/api/admin/rag/sync", summary="Repair the system knowledge index", response_model=APIResponse)
async def sync_system_knowledge_index(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: Any = Depends(get_system_knowledge_manager),
) -> APIResponse:
    del current_admin
    try:
        result = manager.sync_chroma_with_db()
        if not result.get("success"):
            _raise_knowledge_failure(
                result,
                default_code="RAG_SYNC_FAILED",
                default_message="Knowledge index could not be repaired",
            )
        return create_success_response(
            result.get("message", "Knowledge index repaired"),
            data={"deleted_ids_count": result.get("deleted_ids_count", 0)},
        )
    except Exception as exc:
        logger.error("System knowledge index repair failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="Knowledge index could not be repaired",
            error_code="RAG_SYNC_FAILED",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

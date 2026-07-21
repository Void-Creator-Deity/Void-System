"""Unified user-facing library API for private and official knowledge."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Depends, File, Form, Query, Request, UploadFile, status

from api.http.dependencies import get_current_user, get_user_knowledge_resources, get_user_library_catalog
from api.http.responses import APIResponse, create_success_response
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from errors import VoidSystemException
from modules.knowledge.ingestion import IngestSource
from modules.knowledge.quality import answer_support
from modules.knowledge.service import UserKnowledgeResources

logger = logging.getLogger("void-system.library")
router = APIRouter()
LibrarySource = Literal["library", "uploads", "shared"]


def _query_filters(*, tags: Optional[List[str]], include_global_shared: bool) -> Dict[str, Any]:
    """Build retrieval eligibility flags understood by the unified catalogue resolver."""
    return {"tags": tags or [], "include_global_shared": include_global_shared}


def _parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = [part.strip() for part in raw.split(",")]
    if not isinstance(value, list):
        raise VoidSystemException("Tags must be an array or comma-separated text", "INVALID_TAGS", status.HTTP_400_BAD_REQUEST)
    return [str(tag).strip()[:40] for tag in value if str(tag).strip()][:20]


def _citation(citation: Any) -> Dict[str, Any]:
    metadata = dict(citation.metadata or {})
    scope = str(metadata.get("scope") or "")
    return {
        "document_id": citation.document_id,
        "title": citation.title or citation.file_name or citation.document_id[:8],
        "file_name": citation.file_name,
        "score": citation.score or 0,
        "chunk_index": citation.chunk_index,
        "source": "shared" if scope == KnowledgeScope.SYSTEM.value else "upload",
        "metadata": metadata,
    }


@router.get("/api/library/documents", response_model=APIResponse, summary="List one unified knowledge library")
async def list_library_documents(
    source: LibrarySource = Query("library"),
    status_filter: Optional[str] = Query(None, alias="status"),
    retention: Literal["active", "archived", "all"] = Query("active"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    catalog: Any = Depends(get_user_library_catalog),
) -> APIResponse:
    if source != "uploads" and retention == "archived":
        raise VoidSystemException("Archived documents only exist in your private library", "INVALID_LIBRARY_RETENTION", status.HTTP_400_BAD_REQUEST)
    return create_success_response("Library loaded", data=catalog.list_documents(
        owner_id=current_user["user_id"], source=source, status=status_filter,
        retention=retention, limit=limit, offset=offset,
    ))


@router.get("/api/library/stats", response_model=APIResponse, summary="Get unified library statistics")
async def library_stats(
    source: LibrarySource = Query("library"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    catalog: Any = Depends(get_user_library_catalog),
) -> APIResponse:
    return create_success_response("Library summary loaded", data=catalog.stats(current_user["user_id"], source=source))


@router.get("/api/library/tags", response_model=APIResponse, summary="Get visible library tags")
async def library_tags(
    source: LibrarySource = Query("library"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    catalog: Any = Depends(get_user_library_catalog),
) -> APIResponse:
    return create_success_response("Library tags loaded", data={"tags": catalog.list_tags(owner_id=current_user["user_id"], source=source)})


@router.post("/api/library/shared/{document_id}/join", response_model=APIResponse, summary="Add shared material to my library")
async def join_shared_library_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    catalog: Any = Depends(get_user_library_catalog),
) -> APIResponse:
    """Create one user-library reference to a shared record, without copying content."""
    if not catalog.add_shared_document_to_library(owner_id=current_user["user_id"], document_id=document_id):
        raise VoidSystemException("This shared material is unavailable", "SHARED_DOCUMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    return create_success_response("Added to your library", data={"document_id": document_id, "is_in_library": True})


@router.delete("/api/library/shared/{document_id}/join", response_model=APIResponse, summary="Remove shared material from my library")
async def leave_shared_library_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    catalog: Any = Depends(get_user_library_catalog),
) -> APIResponse:
    """Remove only the caller's relationship; the global catalogue item remains intact."""
    if not catalog.remove_shared_document_from_library(owner_id=current_user["user_id"], document_id=document_id):
        raise VoidSystemException("This material is not in your library", "LIBRARY_ENTRY_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    return create_success_response("Removed from your library", data={"document_id": document_id, "is_in_library": False})


@router.post("/api/library/documents/upload", response_model=APIResponse, summary="Upload into my private library")
async def upload_private_library_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    tag_list = _parse_tags(tags)
    results: List[Dict[str, Any]] = []
    for upload in files:
        file_name = upload.filename or "untitled-upload"
        try:
            result = await resources.engine.ingest(IngestSource(
                owner_id=current_user["user_id"], file_name=file_name, content=await upload.read(),
                title=title.strip() if title else None, tags=tag_list, scope=KnowledgeScope.USER,
            ))
        except Exception:
            logger.exception("Library upload failed for %s", file_name)
            result = {"success": False, "message": "The file could not be queued", "error_code": "INGEST_FAILED"}
        results.append({"file_name": file_name, **result})
    successful = sum(bool(result.get("success")) for result in results)
    if successful:
        worker = getattr(request.app.state, "knowledge_job_worker", None)
        if worker is not None:
            worker.wake()
    return create_success_response("Files were added to my library", data={"results": results, "successful_count": successful, "total_count": len(results)})


@router.post("/api/library/search", response_model=APIResponse, summary="Search my library or deliberately expand to shared catalogue")
async def search_library(
    query: str = Body(...),
    include_global_shared: bool = Body(False),
    document_ids: Optional[List[str]] = Body(None),
    tags: Optional[List[str]] = Body(None),
    top_k: int = Body(5, ge=1, le=10),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    question = query.strip()
    if not question:
        raise VoidSystemException("Enter a search query", "EMPTY_QUERY", status.HTTP_400_BAD_REQUEST)
    try:
        results = resources.engine.search(KnowledgeQuery(
            owner_id=current_user["user_id"], question=question,
            scopes=(KnowledgeScope.USER, KnowledgeScope.SYSTEM),
            document_ids=tuple(document_ids or ()), top_k=top_k, mode="hybrid",
            filters=_query_filters(tags=tags, include_global_shared=include_global_shared),
        ))
    except Exception as exc:
        logger.exception("Library search failed")
        raise VoidSystemException("Knowledge search is temporarily unavailable", "KNOWLEDGE_SEARCH_FAILED", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
    return create_success_response("Library search completed", data={
        "include_global_shared": include_global_shared,
        "results": [{"content": item.text, "document_id": item.document_id, "score": item.score, "source": "shared" if item.scope == KnowledgeScope.SYSTEM else "upload", "metadata": {**item.metadata, "title": item.title, "file_name": item.file_name, "chunk_index": item.chunk_index}} for item in results],
    })


@router.post("/api/library/ask", response_model=APIResponse, summary="Ask my library or deliberately expand to shared catalogue")
async def ask_library(
    question: str = Body(...),
    include_global_shared: bool = Body(False),
    document_ids: Optional[List[str]] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    prompt = question.strip()
    if not prompt:
        raise VoidSystemException("Enter a question", "EMPTY_QUESTION", status.HTTP_400_BAD_REQUEST)
    try:
        answer = await resources.engine.ask(KnowledgeQuery(
            owner_id=current_user["user_id"], question=prompt,
            scopes=(KnowledgeScope.USER, KnowledgeScope.SYSTEM),
            document_ids=tuple(document_ids or ()), top_k=6, mode="hybrid",
            filters=_query_filters(tags=tags, include_global_shared=include_global_shared),
        ))
    except Exception as exc:
        logger.exception("Library answer failed")
        raise VoidSystemException("Knowledge service could not answer right now", "KNOWLEDGE_ANSWER_FAILED", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
    return create_success_response("Library answer completed", data={
        "question": prompt, "answer": answer.answer, "confidence": answer.confidence,
        "include_global_shared": include_global_shared, "sources": [_citation(citation) for citation in answer.citations],
        "support": answer_support(answer),
    })

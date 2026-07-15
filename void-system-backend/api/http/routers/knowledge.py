"""HTTP adapter for Knowledge Engine retrieval."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, status

from api.http.dependencies import (
    get_current_user,
    get_system_knowledge_resources,
    get_user_knowledge_resources,
    get_user_knowledge_workspace,
)
from api.http.responses import APIResponse
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from errors import VoidSystemException
from modules.knowledge.quality import answer_support
from modules.knowledge.service import SystemKnowledgeResources, UserKnowledgeResources
from modules.knowledge.workspace import KnowledgeWorkspace


logger = logging.getLogger("void-system.knowledge")
router = APIRouter()


@router.post(
    "/api/knowledge/search",
    summary="检索知识库",
    tags=["知识库"],
    response_model=APIResponse,
)
@router.post(
    "/api/vector/search",
    summary="检索用户文档（兼容接口）",
    tags=["用户文档"],
    response_model=APIResponse,
)
async def search_knowledge(
    query: str = Body(..., embed=True),
    top_k: Optional[int] = Body(3, ge=1, le=10),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    try:
        results = resources.engine.search(
            KnowledgeQuery(
                owner_id=current_user["user_id"],
                question=query.strip(),
                scopes=(KnowledgeScope.USER,),
                top_k=top_k or 3,
                mode="hybrid",
            )
        )
        search_results = [
            {
                "content": result.text,
                "doc_id": result.document_id,
                "score": result.score,
                "metadata": {
                    **result.metadata,
                    "title": result.title,
                    "file_name": result.file_name,
                    "chunk_index": result.chunk_index,
                },
            }
            for result in results
        ]
        return APIResponse(
            success=True,
            message="知识检索成功",
            data={"results": search_results, "mode": "hybrid"},
        )
    except Exception as exc:
        logger.error("知识检索失败: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="知识检索暂时不可用",
            error_code="KNOWLEDGE_SEARCH_FAILED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


@router.post(
    "/api/knowledge/system/search",
    summary="Search shared system knowledge",
    tags=["Knowledge"],
    response_model=APIResponse,
)
async def search_system_knowledge(
    query: str = Body(..., embed=True),
    top_k: Optional[int] = Body(5, ge=1, le=10),
    tags: Optional[list[str]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: SystemKnowledgeResources = Depends(get_system_knowledge_resources),
) -> APIResponse:
    del current_user
    question = query.strip()
    if not question:
        raise VoidSystemException(
            message="Please enter a question to search.",
            error_code="EMPTY_QUERY",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        results = resources.engine.search(
            KnowledgeQuery(
                question=question,
                scopes=(KnowledgeScope.SYSTEM,),
                top_k=top_k or 5,
                mode="hybrid",
                filters={"tags": tags or []},
            )
        )
    except Exception as exc:
        logger.error("System knowledge search failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="System knowledge is temporarily unavailable.",
            error_code="SYSTEM_KNOWLEDGE_SEARCH_FAILED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return APIResponse(
        success=True,
        message="System knowledge search completed",
        data={
            "results": [
                {
                    "content": result.text,
                    "doc_id": result.document_id,
                    "score": result.score,
                    "scope": result.scope.value,
                    "metadata": {
                        **result.metadata,
                        "title": result.title,
                        "file_name": result.file_name,
                        "chunk_index": result.chunk_index,
                    },
                }
                for result in results
            ],
            "mode": "hybrid",
            "scope": KnowledgeScope.SYSTEM.value,
        },
    )


@router.post(
    "/api/knowledge/system/ask",
    summary="Ask shared system knowledge",
    tags=["Knowledge"],
    response_model=APIResponse,
)
async def ask_system_knowledge(
    question: str = Body(..., embed=True),
    tags: Optional[list[str]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: SystemKnowledgeResources = Depends(get_system_knowledge_resources),
) -> APIResponse:
    del current_user
    question = question.strip()
    if not question:
        raise VoidSystemException(
            message="Please enter a question.",
            error_code="EMPTY_QUESTION",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        answer = await resources.engine.ask(
            KnowledgeQuery(
                question=question,
                scopes=(KnowledgeScope.SYSTEM,),
                top_k=6,
                mode="hybrid",
                filters={"tags": tags or []},
            )
        )
    except Exception as exc:
        logger.error("System knowledge answer failed: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="System knowledge could not answer right now.",
            error_code="SYSTEM_KNOWLEDGE_ANSWER_FAILED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return APIResponse(
        success=True,
        message="System knowledge answer completed",
        data={
            "question": question,
            "answer": answer.answer,
            "confidence": answer.confidence,
            "sources": [
                {
                    "doc_id": citation.document_id,
                    "title": citation.title or citation.file_name or citation.document_id[:8],
                    "relevance_score": citation.score or 0,
                    "chunk_index": citation.chunk_index,
                    "tags": citation.metadata.get("tags", []),
                }
                for citation in answer.citations
            ],
            "scope": KnowledgeScope.SYSTEM.value,
            "support": answer_support(answer),
        },
    )


@router.get(
    "/api/user/knowledge/activity",
    summary="获取知识活动",
    tags=["知识库"],
    response_model=APIResponse,
)
async def get_knowledge_activity(
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    """Return recent user-owned knowledge activity without implementation details."""
    activity = workspace.recent_activity(current_user["user_id"], limit=limit)
    return APIResponse(
        success=True,
        message="知识活动已获取",
        data={"activity": activity},
    )

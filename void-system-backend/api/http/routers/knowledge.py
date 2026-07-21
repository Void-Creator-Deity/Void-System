"""HTTP adapter for Knowledge Engine retrieval."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, status

from api.http.dependencies import (
    get_current_user,
    get_user_knowledge_resources,
    get_user_knowledge_workspace,
)
from api.http.responses import APIResponse
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from errors import VoidSystemException
from modules.knowledge.quality import answer_support
from modules.knowledge.service import UserKnowledgeResources
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
    include_global_shared: bool = Body(False),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    try:
        results = resources.engine.search(
            KnowledgeQuery(
                owner_id=current_user["user_id"],
                question=query.strip(),
                scopes=(KnowledgeScope.USER, KnowledgeScope.SYSTEM),
                top_k=top_k or 3,
                mode="hybrid",
                filters={"include_global_shared": include_global_shared},
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
    except VoidSystemException:
        raise
    except Exception as exc:
        logger.error("知识检索失败: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="知识检索暂时不可用",
            error_code="KNOWLEDGE_SEARCH_FAILED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


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

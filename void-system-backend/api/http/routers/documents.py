"""HTTP Adapter for personal knowledge documents and grounded answers."""
import json
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status as http_status,
)

from api.http.dependencies import (
    get_current_user,
    get_user_knowledge_resources,
    get_user_knowledge_workspace,
)
from api.http.responses import APIResponse, create_success_response
from core.knowledge_contracts import IngestSource, KnowledgeQuery, KnowledgeScope
from errors import VoidSystemException
from modules.knowledge.quality import answer_support
from modules.knowledge.service import UserKnowledgeResources
from modules.knowledge.workspace import KnowledgeWorkspace


logger = logging.getLogger("void-system.documents")
router = APIRouter(tags=["个人知识"])


def _parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [part.strip() for part in raw.split(",") if part.strip()]
    if not isinstance(parsed, list):
        raise VoidSystemException(
            message="标签格式无效",
            error_code="INVALID_TAGS",
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )
    return [str(tag).strip()[:40] for tag in parsed if str(tag).strip()][:20]


@router.post("/api/user/documents/upload", summary="添加知识资料", response_model=APIResponse)
async def upload_user_document(
    files: List[UploadFile] = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    if not files:
        raise VoidSystemException(
            message="请至少选择一个文件",
            error_code="NO_FILES",
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )

    tag_list = _parse_tags(tags)
    results = []
    for file in files:
        file_name = file.filename or "未命名资料"
        try:
            result = await resources.engine.ingest(
                IngestSource(
                    owner_id=current_user["user_id"],
                    file_name=file_name,
                    content=await file.read(),
                    title=title.strip() if title else None,
                    tags=tag_list,
                    scope=KnowledgeScope.USER,
                )
            )
        except Exception as exc:
            logger.error("知识资料上传失败 %s: %s", file_name, exc, exc_info=True)
            result = {
                "success": False,
                "message": "文件暂时无法处理",
                "error_code": "INGEST_FAILED",
            }
        results.append({"file_name": file_name, **result})

    successful_count = sum(1 for result in results if result.get("success"))
    data = {
        "results": results,
        "successful_count": successful_count,
        "total_count": len(results),
    }
    if successful_count == 0:
        raise VoidSystemException(
            message="所选文件均未能处理",
            error_code="UPLOAD_FAILED",
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=data,
        )
    return create_success_response(
        f"已添加 {successful_count}/{len(results)} 个文件",
        data=data,
    )


@router.get("/api/user/documents", summary="获取知识资料", response_model=APIResponse)
async def get_user_documents(
    status: Optional[str] = None,
    retention: Literal["active", "archived", "all"] = "active",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    try:
        result = workspace.list_documents(
            current_user["user_id"],
            status=status,
            retention=retention,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("知识资料读取失败: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="资料暂时无法读取",
            error_code="LIST_DOCUMENTS_FAILED",
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return create_success_response("资料读取成功", data=result)


@router.get("/api/user/documents/stats", summary="获取知识空间概况", response_model=APIResponse)
async def get_user_document_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    return create_success_response(
        "知识空间概况读取成功",
        data=workspace.stats(current_user["user_id"]),
    )


@router.post("/api/user/documents/rebuild-index", summary="重新整理个人资料", response_model=APIResponse)
async def rebuild_user_document_index(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    background_tasks.add_task(workspace.rebuild_index, current_user["user_id"])
    return create_success_response("资料整理任务已开始", data={"status": "queued"})


@router.get("/api/user/documents/{doc_id}", summary="获取知识资料详情", response_model=APIResponse)
async def get_user_document(
    doc_id: str,
    include_archived: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    document = workspace.get_document(
        current_user["user_id"], doc_id, include_archived=include_archived
    )
    if document is None:
        raise VoidSystemException(
            message="资料不存在或无权访问",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=http_status.HTTP_404_NOT_FOUND,
        )
    return create_success_response("资料详情读取成功", data=document)


@router.put("/api/user/documents/{doc_id}", summary="更新知识资料信息", response_model=APIResponse)
async def update_user_document(
    doc_id: str,
    title: Optional[str] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    clean_title = title.strip() if title else None
    clean_tags = (
        [tag.strip()[:40] for tag in (tags or []) if tag.strip()][:20]
        if tags is not None
        else None
    )
    if clean_title is None and clean_tags is None:
        raise VoidSystemException(
            message="请至少修改标题或标签",
            error_code="EMPTY_UPDATE",
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )
    updated = workspace.update_document(
        current_user["user_id"], doc_id, title=clean_title, tags=clean_tags
    )
    if not updated:
        raise VoidSystemException(
            message="资料不存在或已归档",
            error_code="DOCUMENT_UPDATE_FAILED",
            status_code=http_status.HTTP_404_NOT_FOUND,
        )
    return create_success_response("资料信息已更新")


@router.delete("/api/user/documents/{doc_id}", summary="归档知识资料", response_model=APIResponse)
async def archive_user_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    archived = workspace.archive_document(current_user["user_id"], doc_id)
    if not archived:
        raise VoidSystemException(
            message="资料不存在或已经归档",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=http_status.HTTP_404_NOT_FOUND,
        )
    return create_success_response(
        "资料已移到回收站",
        data={"retention": "archived", "restorable": True},
    )


@router.post("/api/user/documents/{doc_id}/restore", summary="恢复知识资料", response_model=APIResponse)
async def restore_user_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    restored = workspace.restore_document(current_user["user_id"], doc_id)
    if not restored:
        raise VoidSystemException(
            message="回收站中没有这份资料",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=http_status.HTTP_404_NOT_FOUND,
        )
    return create_success_response("资料已恢复", data={"retention": "active"})


@router.delete("/api/user/documents/{doc_id}/purge", summary="永久清除知识资料", response_model=APIResponse)
async def purge_user_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    result = workspace.purge_document(current_user["user_id"], doc_id)
    if result.get("purged"):
        return create_success_response("资料已永久清除", data=result)
    reason = result.get("reason")
    if reason == "index_unavailable":
        raise VoidSystemException(
            message="检索内容暂时无法清理，资料仍安全保留在回收站中",
            error_code="KNOWLEDGE_PURGE_DEFERRED",
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    raise VoidSystemException(
        message="只能永久清除回收站中的资料",
        error_code="DOCUMENT_NOT_FOUND",
        status_code=http_status.HTTP_404_NOT_FOUND,
    )


@router.get(
    "/api/vector/stats",
    summary="获取知识索引兼容诊断",
    response_model=APIResponse,
    deprecated=True,
)
async def get_vector_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: KnowledgeWorkspace = Depends(get_user_knowledge_workspace),
) -> APIResponse:
    try:
        stats = workspace.index_stats(current_user["user_id"])
    except Exception as exc:
        logger.error("知识索引诊断读取失败: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="知识索引诊断暂时不可用",
            error_code="KNOWLEDGE_STATS_FAILED",
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return create_success_response("知识索引诊断读取成功", data={"stats": stats})


@router.post("/api/user/qa/ask", summary="询问个人知识", response_model=APIResponse)
async def ask_with_user_documents(
    question: str = Body(..., embed=True),
    document_ids: Optional[List[str]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
) -> APIResponse:
    question = question.strip()
    if not question:
        raise VoidSystemException(
            message="请输入想了解的问题",
            error_code="EMPTY_QUESTION",
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )

    stats = resources.workspace.stats(current_user["user_id"])
    if stats.get("completed_documents", 0) == 0:
        return create_success_response(
            "添加资料后即可开始提问",
            data={
                "answer": "这里还没有可检索的资料。先添加文件，处理完成后就可以基于内容提问。",
                "has_documents": False,
                "stats": stats,
                "sources": [],
                "support": {"status": "needs_more_context", "source_count": 0},
            },
        )

    try:
        answer = await resources.engine.ask(
            KnowledgeQuery(
                owner_id=current_user["user_id"],
                question=question,
                document_ids=document_ids,
                scopes=(KnowledgeScope.USER,),
                top_k=6,
                mode="hybrid",
            )
        )
    except Exception as exc:
        logger.error("个人知识问答失败: %s", exc, exc_info=True)
        raise VoidSystemException(
            message="暂时无法完成回答，请稍后重试",
            error_code="KNOWLEDGE_ANSWER_FAILED",
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    sources = [
        {
            "doc_id": citation.document_id,
            "title": citation.title or citation.file_name or citation.document_id[:8],
            "chunk_index": citation.chunk_index,
        }
        for citation in answer.citations
    ]
    return create_success_response(
        "回答完成",
        data={
            "question": question,
            "answer": answer.answer,
            "sources": sources,
            "confidence": answer.confidence,
            "retrieved_docs_count": len({citation.document_id for citation in answer.citations}),
            "has_documents": True,
            "stats": stats,
            "support": answer_support(answer),
        },
    )

"""Planning use cases for persisted, user-reviewable Plan Drafts."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from adapters.sqlite.plan_draft_repository import SQLitePlanDraftRepository
from database import Database
from errors import VoidSystemException
from modules.tasks.execution import TaskExecution
from core.task_execution_contracts import TaskExecutionError
from modules.tasks.service import get_task_execution


class PlanDraftService:
    """Own draft access, validation, optimistic editing, and atomic publication.

    Inputs:
        repository: Durable owner-scoped Plan Draft storage; execution: canonical Goal/Run validator.
    Outputs:
        Authoritative draft snapshots, including published Goal/Run identifiers when applicable.
    Called by:
        Planning HTTP routes and the background generation completion path through the repository.
    Side effects:
        Persists edits and invokes one transactional publication adapter operation.
    Failure:
        Raises stable VoidSystemException codes for missing resources, version races, invalid drafts,
        and publication conflicts. SQLite errors remain infrastructure failures.
    Invariants:
        Editable drafts are normalized by the same TaskExecution rules that govern direct Goal/Run
        creation; the browser never owns publication state.
    """

    def __init__(self, repository: SQLitePlanDraftRepository, execution: TaskExecution) -> None:
        self._repository = repository
        self._execution = execution

    def list_recent(self, user_id: str, *, limit: int = 30) -> Sequence[Dict[str, Any]]:
        """Return only the requesting user's persisted plan history."""
        return self._repository.list_recent(user_id, limit=limit)

    def get(self, user_id: str, draft_id: str) -> Dict[str, Any]:
        """Read an owner-scoped Plan Draft or return the stable not-found contract."""
        draft = self._repository.get(user_id, draft_id)
        if draft is None:
            raise VoidSystemException("方案草稿不存在或无权访问", "PLAN_DRAFT_NOT_FOUND", 404)
        return draft

    def update(self, user_id: str, draft_id: str, payload: Mapping[str, Any], expected_version: int) -> Dict[str, Any]:
        """Validate and persist a user edit guarded by the previously rendered version.

        Inputs:
            Owner, draft id, editable plan payload, and optimistic version from the latest GET.
        Outputs:
            The normalized authoritative draft snapshot.
        Called by:
            PATCH /api/plan-drafts/{draft_id}; the Advisor explicit save action.
        Side effects:
            Replaces the persisted draft payload and increments its version.
        Failure:
            Rejects missing/published drafts, invalid Goal/Run shapes, and stale browser edits.
        Invariants:
            The stored payload is publishable by TaskExecution validation and cannot create a second
            user-owned execution model.
        """
        current = self.get(user_id, draft_id)
        if current["status"] != "ready":
            raise VoidSystemException("已发布的方案不能再编辑", "PLAN_DRAFT_NOT_EDITABLE", 409)
        normalized = self._normalize_payload(payload)
        updated = self._repository.update(user_id, draft_id, normalized, expected_version)
        if updated is None:
            latest = self.get(user_id, draft_id)
            if latest["status"] != "ready":
                raise VoidSystemException("方案已经发布，无法覆盖", "PLAN_DRAFT_NOT_EDITABLE", 409)
            raise VoidSystemException("方案已在其他位置修改，请刷新后再保存", "PLAN_DRAFT_VERSION_CONFLICT", 409)
        return updated

    def publish(self, user_id: str, draft_id: str, idempotency_key: str) -> Dict[str, Any]:
        """Publish one persisted draft to the canonical Goal/Run execution model.

        Inputs:
            Owner, draft id, and a stable non-empty key reused across browser retries.
        Outputs:
            Published draft snapshot with published_goal_id and published_run_id.
        Called by:
            POST /api/plan-drafts/{draft_id}/publish from the Advisor confirmation action.
        Side effects:
            Delegates one SQLite transaction that creates Goal, Run, Step, dependency, and events.
        Failure:
            Returns stable errors for missing, non-ready, invalid, or conflicting publications; no
            partial execution records are committed when validation or persistence fails.
        Invariants:
            Same owner/draft/key is idempotent. A user cannot publish an edited draft without server
            validation, and the initial Run is immediately in the canonical running state.
        """
        draft = self.get(user_id, draft_id)
        if draft["status"] == "published":
            if draft.get("publication_key") == idempotency_key:
                return draft
            raise VoidSystemException("该方案已经开始推进", "PLAN_DRAFT_ALREADY_PUBLISHED", 409)
        if draft["status"] != "ready":
            raise VoidSystemException("方案尚未准备好发布", "PLAN_DRAFT_NOT_READY", 409)
        normalized = self._normalize_payload(draft["payload"])
        try:
            published = self._repository.publish(user_id, draft_id, idempotency_key, normalized)
        except ValueError as exc:
            code = str(exc)
            if code == "PLAN_DRAFT_ALREADY_PUBLISHED":
                raise VoidSystemException("该方案已经开始推进", code, 409) from exc
            if code == "PLAN_DRAFT_IDEMPOTENCY_CONFLICT":
                raise VoidSystemException("该发布请求已被用于另一份方案", code, 409) from exc
            raise VoidSystemException("方案步骤关联无效，请重新保存后发布", "PLAN_DRAFT_INVALID", 422) from exc
        if published is None:
            raise VoidSystemException("方案草稿不存在或无权访问", "PLAN_DRAFT_NOT_FOUND", 404)
        return published


    def _normalize_payload(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Translate TaskExecution validation errors into the Plan Draft HTTP error contract.

        Inputs:
            payload: Editable Goal/Run plan object supplied by a draft save or publication request.
        Outputs:
            Canonical normalized execution specification.
        Called by:
            update and publish before any persistence transition.
        Side effects:
            None.
        Failure:
            Converts domain validation errors into a user-safe PLAN_DRAFT_INVALID response.
        Invariants:
            All Plan Draft paths use the same validator instead of reimplementing field rules.
        """
        try:
            return self._execution.normalize_plan_draft(payload)
        except TaskExecutionError as exc:
            raise VoidSystemException("方案内容不完整，请检查目标和步骤", "PLAN_DRAFT_INVALID", 422) from exc


def get_plan_draft_service(database: Database) -> PlanDraftService:
    """Compose the single Plan Draft use case from application database dependencies."""
    return PlanDraftService(SQLitePlanDraftRepository(database.get_connection), get_task_execution(database))

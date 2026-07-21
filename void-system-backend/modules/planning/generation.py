"""Durable plan-generation jobs and the canonical one-pass planner call."""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, Mapping, Optional

from adapters.sqlite.plan_generation_repository import SQLitePlanGenerationRepository
from core.planning_contracts import PlanRequest, UserCapability
from core.runtime_settings import RuntimeSettings
from database import Database
from errors import VoidSystemException
from modules.growth.profile import GrowthProfile
from modules.personal_context.service import PersonalContext
from modules.planning.context import build_generation_context
from modules.planning.interaction import resolve_planning_interaction_policy
from modules.planning.service import get_planning_engine


logger = logging.getLogger("void-system.planning")


class PlanGenerationService:
    """Own durable plan-job validation, lease-aware execution, and owner access.

    Router code creates and reads jobs through this service. The worker claims persisted jobs,
    then invokes execute_claimed; neither browser connections nor FastAPI request lifetimes own
    the generation lifecycle.
    """

    def __init__(self, repository: SQLitePlanGenerationRepository) -> None:
        self._repository = repository

    def create(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Validate a submitted request and store an authoritative queued job snapshot."""
        topic = str(values.get("topic") or "").strip()
        if not topic:
            raise VoidSystemException("主题不能为空", "TOPIC_REQUIRED", 400)
        return self._repository.create(
            user_id,
            {
                "topic": topic,
                "execution_mode": str(values.get("execution_mode") or "assisted"),
                "max_steps": int(values.get("max_steps") or 8),
                "advisor_prefs": dict(values.get("advisor_prefs") or {}),
            },
        )

    def get(self, user_id: str, generation_id: str) -> Dict[str, Any]:
        """Return one owner-scoped persisted job or a stable not-found error."""
        job = self._repository.get(user_id, generation_id)
        if job is None:
            raise VoidSystemException("生成任务不存在或无权访问", "PLAN_GENERATION_NOT_FOUND", 404)
        return job

    def list_recent(self, user_id: str, *, limit: int = 20) -> list[Dict[str, Any]]:
        """List durable jobs for refresh recovery and the global progress center."""
        return self._repository.list_recent(user_id, limit=limit)

    def cancel(self, user_id: str, generation_id: str) -> Dict[str, Any]:
        """Persist cancellation; active model calls stop cooperatively at their next checkpoint."""
        job = self._repository.cancel(user_id, generation_id)
        if job is None:
            raise VoidSystemException("生成任务不存在或无权访问", "PLAN_GENERATION_NOT_FOUND", 404)
        return job

    def claim_next_for_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Atomically lease the next persisted request for the named application worker."""
        return self._repository.claim_next(worker_id)

    def execute_claimed(
        self,
        job: Mapping[str, Any],
        generate: Callable[[Mapping[str, Any], Callable[[str, int], bool]], Dict[str, Any]],
    ) -> None:
        """Run one worker-leased job and publish only the resulting complete draft.

        Inputs:
            job: Snapshot returned by the repository's atomic claim, including its private lease.
            generate: Application-composed callback that resolves user context and calls the planner.
        Outputs:
            None. The authoritative ready/failed/cancelled state is persisted by the repository.
        Called by:
            PlanGenerationWorker after it claims a database job.
        Side effects:
            Renews the lease at checkpoints and writes progress, result, or a safe failure message.
        Failure:
            Domain errors become a user-safe failed job. Unexpected errors are logged without leaking
            provider credentials or internal prompt content.
        Invariants:
            A stale worker cannot update, publish, or overwrite a job reclaimed by another worker.
        """
        generation_id = str(job["generation_id"])
        worker_id = str(job.get("worker_id") or "")
        lease_token = str(job.get("lease_token") or "")
        if not worker_id or not lease_token:
            logger.error("Plan worker received an unleased generation job")
            return

        def report(stage: str, progress: int) -> bool:
            if self._repository.is_cancel_requested(generation_id, worker_id, lease_token):
                return False
            if not self._repository.heartbeat(generation_id, worker_id, lease_token):
                return False
            return self._repository.update_progress(
                generation_id, worker_id, lease_token, stage, progress
            )

        if not report("preparing_context", 20):
            self._repository.fail(generation_id, worker_id, lease_token, "")
            return
        try:
            result = generate(job, report)
            if self._repository.is_cancel_requested(generation_id, worker_id, lease_token):
                self._repository.fail(generation_id, worker_id, lease_token, "")
                return
            self._repository.heartbeat(generation_id, worker_id, lease_token)
            self._repository.complete(generation_id, worker_id, lease_token, result)
        except VoidSystemException as exc:
            self._repository.fail(generation_id, worker_id, lease_token, exc.message)
        except Exception as exc:
            logger.error("Plan generation job failed (%s)", type(exc).__name__)
            self._repository.fail(
                generation_id, worker_id, lease_token, "规划服务暂时不可用，请重新生成。"
            )


class PlanGenerationWorker:
    """Application-owned polling worker for the persistent plan-generation queue.

    Inputs:
        service: Lease-aware plan generation service.
        execute_claimed: Callback that composes application dependencies for each persisted job.
    Outputs:
        A daemon worker that can be started, woken after submission, and stopped at shutdown.
    Called by:
        FastAPI lifespan; HTTP submission only signals it and never owns execution.
    Side effects:
        Continuously claims queued SQLite jobs and invokes model generation outside request handlers.
    Failure:
        Logs unexpected callback failures and lets the lease expire for safe later recovery.
    Invariants:
        The worker has no authoritative in-memory queue. SQLite remains the source of truth.
    """

    def __init__(
        self,
        service: PlanGenerationService,
        execute_claimed: Callable[[Mapping[str, Any]], None],
        *,
        poll_seconds: float = 1.0,
    ) -> None:
        self._service = service
        self._execute_claimed = execute_claimed
        self._poll_seconds = max(0.1, poll_seconds)
        self._worker_id = f"plan-worker-{uuid.uuid4()}"
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start one application worker exactly once during lifespan startup."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name=self._worker_id, daemon=True
        )
        self._thread.start()

    def wake(self) -> None:
        """Prompt the worker to claim newly submitted work without waiting for the next poll."""
        self._wake.set()

    def stop(self, *, timeout: float = 5.0) -> None:
        """Request graceful worker shutdown; persisted leases remain recoverable after process exit."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            job = self._service.claim_next_for_worker(self._worker_id)
            if job is None:
                self._wake.wait(self._poll_seconds)
                self._wake.clear()
                continue
            try:
                self._execute_claimed(job)
            except Exception as exc:
                logger.error("Plan worker callback failed (%s)", type(exc).__name__)

def get_plan_generation_service(database: Database) -> PlanGenerationService:
    return PlanGenerationService(SQLitePlanGenerationRepository(database.get_connection))


def generate_run_plan_draft(
    *,
    current_user: Mapping[str, Any],
    profile: GrowthProfile,
    companion: PersonalContext,
    settings: RuntimeSettings,
    topic: str,
    execution_mode: str,
    max_steps: int,
    advisor_prefs: Optional[Mapping[str, Any]] = None,
    progress_callback: Optional[Callable[[str, int], Any]] = None,
) -> Dict[str, Any]:
    user_id = str(current_user["user_id"])
    companion_settings = companion.get_settings(user_id)
    interaction_policy = resolve_planning_interaction_policy(companion_settings)
    user_attributes = profile.list_capabilities(user_id)
    if progress_callback:
        progress_callback("preparing_context", 30)
    profile_context, context_manifest = _planning_context(
        companion, current_user, user_attributes, dict(advisor_prefs or {})
    )
    capabilities = [
        UserCapability(
            id=str(attribute.get("attr_id") or ""),
            name=str(attribute.get("attr_name") or ""),
            value=int(attribute.get("attr_value") or 0),
            max_value=int(attribute.get("max_value") or 100),
            description=str(attribute.get("description") or ""),
        )
        for attribute in user_attributes
    ]
    if progress_callback:
        progress_callback("generating_steps", 45)
    planner_mode = "single_task" if max_steps == 1 else "workflow_chain"
    plan = get_planning_engine(settings).plan(
        PlanRequest(
            topic=topic,
            profile_context=profile_context,
            capabilities=capabilities,
            mode=planner_mode,
            max_steps=max_steps,
            strict=False,
            interaction_policy=interaction_policy,
        )
    )
    if progress_callback:
        progress_callback("checking_result", 85)
    result = _serialize_run_plan(
        plan, topic=topic, execution_mode=execution_mode, max_steps=max_steps
    )
    result["context"] = context_manifest
    return result


def _planning_context(
    companion: PersonalContext,
    current_user: Mapping[str, Any],
    user_attributes: list[Dict[str, Any]],
    advisor_preferences: Dict[str, Any],
) -> tuple[str, Dict[str, Any]]:
    baseline = build_generation_context(
        dict(current_user), user_attributes, advisor_preferences=advisor_preferences
    )
    snapshot = companion.build_ai_context(
        str(current_user["user_id"]), dict(current_user), purpose="planning_assist"
    )
    personal = companion.render_ai_context(snapshot)
    return (
        baseline + ("\n\nConfirmed personal context:\n" + personal if personal else ""),
        snapshot["manifest"],
    )


def _serialize_task(task: Any) -> Dict[str, Any]:
    title = str(getattr(task, "title", "") or "").strip()
    description = str(getattr(task, "description", "") or "").strip()
    priority = str(getattr(task, "priority", "") or "").strip()
    completion_type = str(getattr(task, "completion_type", "") or "").strip()
    task_type = str(getattr(task, "task_type", "") or "").strip()
    criteria = getattr(task, "completion_criteria", None)
    related_attrs = getattr(task, "related_attrs", None)
    attribute_plan = getattr(task, "attribute_plan", None)
    try:
        estimated_time = int(getattr(task, "estimated_time", 0) or 0)
        reward_growth_points = int(getattr(task, "reward_growth_points", 0) or 0)
        attribute_points = int(getattr(task, "attribute_points", 0) or 0)
    except (TypeError, ValueError):
        estimated_time = reward_growth_points = attribute_points = -1
    valid = (
        title and description and 1 <= estimated_time <= 480 and 0 <= reward_growth_points <= 1000
        and 0 <= attribute_points <= 100 and priority in {"easy", "medium", "hard"}
        and completion_type in {"simple", "progress", "ai_eval", "submission"}
        and task_type in {"main", "side", "daily"} and isinstance(criteria, dict)
        and isinstance(related_attrs, dict) and isinstance(attribute_plan, list)
    )
    if not valid:
        raise VoidSystemException("规划结果不完整，请重新生成后再发布", "PLANNING_INVALID_RUN_SPEC", 422)
    return {
        "title": title, "description": description, "estimated_time": estimated_time,
        "reward_growth_points": reward_growth_points, "attribute_points": attribute_points,
        "priority": priority, "task_type": task_type, "completion_type": completion_type,
        "related_attrs": related_attrs, "completion_criteria": criteria, "attribute_plan": attribute_plan,
    }


def _serialize_run_plan(plan: Any, *, topic: str, execution_mode: str, max_steps: int) -> Dict[str, Any]:
    tasks = [_serialize_task(task) for task in plan.tasks]
    if not tasks or len(tasks) > max_steps:
        raise VoidSystemException("规划结果不完整，请调整目标后重新生成", "PLANNING_INVALID_RUN_SPEC", 422)
    steps = []
    previous_key = None
    for index, task in enumerate(tasks, start=1):
        key = f"step-{index}"
        steps.append({
            "client_key": key, "title": task["title"], "description": task["description"],
            "kind": "manual",
            "depends_on": [previous_key] if previous_key else [],
            "max_attempts": 1,
            "requires_approval": False,
            "completion_criteria": task["completion_criteria"],
            "input_data": {
                "estimated_minutes": task["estimated_time"],
                "capability_plan": task["attribute_plan"],
            },
            # A reviewed plan may propose points before publication; execution only reads this persisted value.
            "reward_spec": {"growth_points": task["reward_growth_points"]},
        })
        previous_key = key
    metadata = plan.metadata if isinstance(plan.metadata, dict) else {}
    return {
        "goal": {
            "title": topic[:160], "description": str(plan.response or "").strip(),
            "desired_outcome": topic, "priority": "medium",
        },
        "run": {"title": topic[:160], "objective": topic, "mode": execution_mode, "steps": steps},
        "summary": str(plan.response or "").strip(),
        "estimated_duration": str(plan.estimated_duration or "").strip(),
        "meta": {"needs_review": True, "used_fallback": bool(metadata.get("fallback", False))},
    }

"""Durable Goal, Run, and Step execution for manual and assisted work."""
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional, Sequence

from core.task_execution_contracts import (
    GOAL_STATUSES,
    RUN_MODES,
    RUN_STATUSES,
    SATISFIED_STEP_STATUSES,
    STEP_KINDS,
    STEP_STATUSES,
    TERMINAL_RUN_STATUSES,
    RunReviewMemoryCandidateSink,
    RunReviewObservationSink,
    TaskExecutionError,
    TaskExecutionRepository,
)
from core.planning_contracts import EvaluationEngine, EvaluationRequest


logger = logging.getLogger(__name__)


class TaskExecution:
    """Own execution policy behind a compact command and query Interface."""

    def __init__(
        self,
        repository: TaskExecutionRepository,
        run_review_observation_sink: RunReviewObservationSink | None = None,
        run_review_memory_candidate_sink: RunReviewMemoryCandidateSink | None = None,
        evaluation_engine: EvaluationEngine | None = None,
    ) -> None:
        self._repository = repository
        self._run_review_observation_sink = run_review_observation_sink
        self._run_review_memory_candidate_sink = run_review_memory_candidate_sink
        self._evaluation_engine = evaluation_engine

    def create_goal(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        title = self._required_text(values.get("title"), "Goal title", 160)
        return self._repository.create_goal(
            user_id,
            {
                "title": title,
                "description": self._text(values.get("description"), 2000),
                "desired_outcome": self._text(values.get("desired_outcome"), 2000),
                "priority": self._choice(values.get("priority") or "medium", {"low", "medium", "high"}, "priority"),
                "idempotency_key": self._optional_text(values.get("idempotency_key"), 200),
                "metadata": self._mapping(values.get("metadata")),
            },
        )

    def list_goals(self, user_id: str, status: Optional[str] = None) -> Sequence[Dict[str, Any]]:
        if status is not None and status not in GOAL_STATUSES:
            raise TaskExecutionError("Invalid goal status.", "INVALID_GOAL_STATUS")
        return self._repository.list_goals(user_id, status)

    def get_goal(self, user_id: str, goal_id: str) -> Dict[str, Any]:
        goal = self._repository.get_goal(user_id, goal_id)
        if goal is None:
            raise TaskExecutionError("Goal not found.", "GOAL_NOT_FOUND", 404)
        return goal

    def update_goal(
        self, user_id: str, goal_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        goal = self.get_goal(user_id, goal_id)
        updates: Dict[str, Any] = {}
        if "title" in values:
            updates["title"] = self._required_text(values.get("title"), "Goal title", 160)
        if "description" in values:
            updates["description"] = self._text(values.get("description"), 2000)
        if "desired_outcome" in values:
            updates["desired_outcome"] = self._text(values.get("desired_outcome"), 2000)
        if "priority" in values:
            updates["priority"] = self._choice(values.get("priority"), {"low", "medium", "high"}, "priority")
        if "metadata" in values:
            updates["metadata"] = self._mapping(values.get("metadata"))
        if "status" in values:
            status = self._choice(values.get("status"), GOAL_STATUSES, "goal status")
            allowed = {
                "active": {"active", "completed", "archived"},
                "completed": {"completed", "active", "archived"},
                "archived": {"archived", "active"},
            }
            if status not in allowed[goal["status"]]:
                raise TaskExecutionError("Invalid goal status transition.", "GOAL_STATE_CONFLICT", 409)
            updates["status"] = status
        if not updates:
            return goal
        if not self._repository.update_goal(user_id, goal_id, updates):
            raise TaskExecutionError("Goal changed before it could be updated.", "GOAL_STATE_CONFLICT", 409)
        return self.get_goal(user_id, goal_id)

    def normalize_plan_draft(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Validate an editable Plan Draft using the canonical Goal/Run execution rules.

        Inputs:
            payload: User-editable object containing goal, run, optional summary, duration, context,
            and metadata fields. It must not contain persistent Goal/Run identifiers.
        Outputs:
            A normalized, publishable plan object with validated Goal fields, Run mode, Step graph,
            object-shaped metadata, and bounded text values.
        Called by:
            PlanDraftService on each saved edit and immediately before atomic publication.
        Side effects:
            None. This is a pure Domain validation boundary shared by draft editing and publishing.
        Failure:
            Raises TaskExecutionError with stable validation semantics for invalid text, mode, JSON
            shape, duplicate step keys, or cyclic/unknown dependencies.
        Invariants:
            The normalized result can be inserted into the only Goal/Run execution model; a browser
            cannot smuggle legacy task fields or an unvalidated dependency graph into persistence.
        """
        raw = self._mapping(payload)
        raw_goal = self._mapping(raw.get("goal"))
        raw_run = self._mapping(raw.get("run"))
        goal = {
            "title": self._required_text(raw_goal.get("title"), "Goal title", 160),
            "description": self._text(raw_goal.get("description"), 2000),
            "desired_outcome": self._text(raw_goal.get("desired_outcome"), 2000),
            "priority": self._choice(raw_goal.get("priority") or "medium", {"low", "medium", "high"}, "priority"),
            "metadata": self._mapping(raw_goal.get("metadata")),
        }
        mode = self._choice(raw_run.get("mode") or "manual", RUN_MODES, "run mode")
        raw_steps = raw_run.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise TaskExecutionError("A plan draft needs at least one step.", "RUN_SPEC_INVALID")
        steps = self._normalize_steps(raw_steps)
        self._validate_graph(steps)
        run = {
            "title": self._required_text(raw_run.get("title") or goal["title"], "Run title", 160),
            "objective": self._text(raw_run.get("objective") or goal["desired_outcome"], 2000),
            "mode": mode,
            "metadata": self._mapping(raw_run.get("metadata")),
            "steps": steps,
        }
        normalized = {
            "goal": goal,
            "run": run,
            "summary": self._text(raw.get("summary"), 5000),
            "estimated_duration": self._text(raw.get("estimated_duration"), 200),
            "context": self._mapping(raw.get("context")),
            "meta": self._mapping(raw.get("meta")),
        }
        return normalized

    def validate_run_template(
        self,
        user_id: str,
        goal_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Normalize a reusable Run template without creating persistence records."""
        goal = self.get_goal(user_id, goal_id)
        if goal["status"] != "active":
            raise TaskExecutionError("Only active goals can start a new run.", "GOAL_NOT_ACTIVE", 409)
        mode = self._choice(values.get("mode") or "manual", RUN_MODES, "run mode")
        raw_steps = values.get("steps") or [
            {
                "client_key": "work",
                "title": values.get("title") or goal["title"],
                "description": values.get("objective") or goal.get("desired_outcome") or goal.get("description", ""),
                "kind": "manual",
            }
        ]
        steps = self._normalize_steps(raw_steps)
        self._validate_graph(steps)
        return {
            "title": self._required_text(values.get("title") or goal["title"], "Run title", 160),
            "objective": self._text(values.get("objective") or goal.get("desired_outcome"), 2000),
            "mode": mode,
            "idempotency_key": self._optional_text(values.get("idempotency_key"), 200),
            "metadata": self._mapping(values.get("metadata")),
            "steps": steps,
        }

    def create_run(
        self,
        user_id: str,
        goal_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        template = self.validate_run_template(user_id, goal_id, values)
        steps = template.pop("steps")
        try:
            return self._repository.create_run(user_id, goal_id, template, steps)
        except ValueError as exc:
            raise TaskExecutionError(str(exc), "RUN_SPEC_INVALID") from exc

    def list_runs(
        self,
        user_id: str,
        *,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]:
        if status is not None and status not in RUN_STATUSES:
            raise TaskExecutionError("Invalid run status.", "INVALID_RUN_STATUS")
        if goal_id is not None:
            self.get_goal(user_id, goal_id)
        return self._repository.list_runs(user_id, goal_id=goal_id, status=status)

    def summarize_profile_behavior(self, user_id: str) -> Dict[str, Any]:
        """Expose conservative aggregate history to Personal Context without raw content."""
        return self._repository.summarize_profile_behavior(user_id)

    def get_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        run = self._repository.get_run(user_id, run_id)
        if run is None:
            raise TaskExecutionError("Run not found.", "RUN_NOT_FOUND", 404)
        return run

    def start_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        self._require_run_status(user_id, run_id, {"queued"})
        if not self._repository.apply_run_transition(
            user_id, run_id, ["queued"], "running", "run.started",
            publish_ready_steps=True,
        ):
            raise TaskExecutionError(
                "Run changed before it could start.", "RUN_STATE_CONFLICT", 409
            )
        return self.get_run(user_id, run_id)

    def pause_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        self._require_run_status(user_id, run_id, {"running"})
        if not self._repository.apply_run_transition(
            user_id, run_id, ["running"], "paused", "run.paused"
        ):
            raise TaskExecutionError(
                "Run changed before it could pause.", "RUN_STATE_CONFLICT", 409
            )
        return self.get_run(user_id, run_id)

    def resume_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        self._require_run_status(user_id, run_id, {"paused"})
        if not self._repository.apply_run_transition(
            user_id, run_id, ["paused"], "running", "run.resumed",
            publish_ready_steps=True,
        ):
            raise TaskExecutionError(
                "Run changed before it could resume.", "RUN_STATE_CONFLICT", 409
            )
        return self.get_run(user_id, run_id)

    def cancel_run(self, user_id: str, run_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        run = self.get_run(user_id, run_id)
        if run["status"] in {"completed", "failed", "cancelled"}:
            if run["status"] == "cancelled":
                return run
            raise TaskExecutionError("A finished run cannot be cancelled.", "RUN_ALREADY_FINISHED", 409)
        if not self._repository.apply_run_transition(
            user_id, run_id, [run["status"]], "cancelled", "run.cancelled",
            payload={"reason": reason}, cancel_open_steps=True,
        ):
            raise TaskExecutionError(
                "Run changed before it could be cancelled.", "RUN_STATE_CONFLICT", 409
            )
        return self.get_run(user_id, run_id)

    def retry_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"failed"})
        retryable_steps = [
            step for step in run.get("steps", [])
            if step["status"] == "failed" and int(step["attempt_count"]) < int(step["max_attempts"])
        ]
        if not retryable_steps:
            raise TaskExecutionError(
                "This action has no failed step with retries remaining.",
                "RUN_RETRY_NOT_AVAILABLE",
                409,
            )
        return self.retry_step(user_id, run_id, retryable_steps[0]["step_id"])

    def start_step(self, user_id: str, run_id: str, step_id: str) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running"})
        step = self._find_step(run, step_id)
        if step["status"] != "ready":
            raise TaskExecutionError("Only a ready step can start.", "STEP_NOT_READY", 409)
        if int(step["attempt_count"]) >= int(step["max_attempts"]):
            raise TaskExecutionError("This step has no retry attempts remaining.", "STEP_ATTEMPTS_EXHAUSTED", 409)
        if step.get("requires_approval") and not self._has_approved_decision(run, step_id):
            return self.request_approval(
                user_id,
                run_id,
                step_id,
                {"summary": "开始这一步前，需要你先确认。"},
            )["run"]
        result = self._repository.apply_step_transition(
            user_id, run_id, step_id, ["ready"], "running", "step.started",
            payload={"attempt": int(step["attempt_count"]) + 1},
            increment_attempt=True,
        )
        if not result.get("changed"):
            raise TaskExecutionError("Step changed before it could start.", "STEP_STATE_CONFLICT", 409)
        return self.get_run(user_id, run_id)

    def skip_step(self, user_id: str, run_id: str, step_id: str) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running"})
        step = self._find_step(run, step_id)
        if step["status"] in SATISFIED_STEP_STATUSES:
            return run
        if step["status"] not in {"pending", "ready", "failed"}:
            raise TaskExecutionError("This step cannot be skipped now.", "STEP_NOT_SKIPPABLE", 409)
        result = self._repository.apply_step_transition(
            user_id, run_id, step_id, [step["status"]], "skipped", "step.skipped",
            publish_ready_steps=True, complete_run_if_satisfied=True,
        )
        if not result.get("changed"):
            raise TaskExecutionError("Step changed before it could be skipped.", "STEP_STATE_CONFLICT", 409)
        return self.get_run(user_id, run_id)

    def complete_step(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        *,
        output_data: Optional[Mapping[str, Any]] = None,
        artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running"})
        if run["mode"] != "manual":
            raise TaskExecutionError(
                "System-assisted steps must be submitted for review.",
                "ASSISTED_REVIEW_REQUIRED",
                409,
            )
        step = self._find_step(run, step_id)
        if step["status"] != "running":
            raise TaskExecutionError("Only a running step can complete.", "STEP_NOT_RUNNING", 409)
        normalized_artifacts = self._normalize_artifacts(artifacts)
        result = self._repository.apply_step_transition(
            user_id, run_id, step_id, ["running"], "completed", "step.completed",
            output_data=output_data or {}, artifacts=normalized_artifacts,
            publish_ready_steps=True, complete_run_if_satisfied=True,
        )
        if not result.get("changed"):
            raise TaskExecutionError(
                "Step changed before completion was saved.", "STEP_STATE_CONFLICT", 409
            )
        return self.get_run(user_id, run_id)

    def review_assisted_step(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Review explicit user evidence and complete a system-assisted step only on approval.

        Inputs: a running assisted Run, its running Step, user-authored evidence, and optional
        artifact references. Output: the refreshed Run with the durable review Action. Called by
        the review HTTP command. Evidence is saved before the model is called, so a provider
        outage is visible and retryable rather than losing the user's submission.
        """
        run = self._require_run_status(user_id, run_id, {"running"})
        if run["mode"] != "assisted":
            raise TaskExecutionError("This run does not use system review.", "REVIEW_NOT_ENABLED", 409)
        step = self._find_step(run, step_id)
        if step["status"] != "running":
            raise TaskExecutionError("Only a running step can be reviewed.", "STEP_NOT_RUNNING", 409)
        submission = self._required_text(values.get("submission"), "Submission", 8000)
        artifacts = self._normalize_artifacts(values.get("artifacts"))
        action = self._repository.create_action(
            user_id,
            run_id,
            step_id,
            {
                "action_type": "system_review_submission",
                "input_data": {
                    "submission": submission,
                    "artifacts": artifacts,
                    "completion_criteria": self._mapping(step.get("completion_criteria")),
                },
                "idempotency_key": self._optional_text(values.get("idempotency_key"), 200),
            },
        )
        if not action.pop("_created", False):
            return self.get_run(user_id, run_id)
        if self._evaluation_engine is None:
            self._repository.complete_action(
                user_id, run_id, step_id, action["action_id"], "unavailable",
                output_data={"feedback": "The AI review service is not configured."},
            )
            return self.get_run(user_id, run_id)
        task = {
            "task_name": step.get("title") or run.get("title") or "Task step",
            "description": step.get("description") or "",
            "completion_criteria": self._mapping(step.get("completion_criteria")),
        }
        try:
            result = self._evaluation_engine.evaluate(
                EvaluationRequest(
                    task=task,
                    submission={
                        "submission": submission,
                        "media_urls": [item["uri"] for item in artifacts if item.get("uri")],
                        "artifacts": artifacts,
                    },
                    user_stats={"attributes": []},
                )
            )
        except Exception:
            logger.exception("System-assisted step review failed", extra={"run_id": run_id, "step_id": step_id})
            self._repository.complete_action(
                user_id, run_id, step_id, action["action_id"], "unavailable",
                output_data={"feedback": "The AI review service is temporarily unavailable. Your evidence was saved."},
            )
            return self.get_run(user_id, run_id)

        approved = result.status == "pass" and int(result.score) >= 70
        output = {
            "approved": approved,
            "feedback": self._text(result.feedback, 4000),
            "score": max(0, min(100, int(result.score))),
            "raw": self._mapping(result.raw),
        }
        action_status = "confirmed" if approved else "revision_requested"
        if not self._repository.complete_action(
            user_id, run_id, step_id, action["action_id"], action_status, output_data=output
        ):
            raise TaskExecutionError("Review changed before it could be saved.", "ACTION_STATE_CONFLICT", 409)
        if not approved:
            return self.get_run(user_id, run_id)
        transition = self._repository.apply_step_transition(
            user_id, run_id, step_id, ["running"], "completed", "step.completed_after_review",
            output_data={"submission": submission, "review": output}, artifacts=artifacts,
            publish_ready_steps=True, complete_run_if_satisfied=True,
        )
        if not transition.get("changed"):
            raise TaskExecutionError("Review passed but the step changed before completion.", "STEP_STATE_CONFLICT", 409)
        return self.get_run(user_id, run_id)

    def fail_step(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        error_summary: str,
    ) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running", "waiting_approval"})
        step = self._find_step(run, step_id)
        if step["status"] not in {"running", "waiting_approval"}:
            raise TaskExecutionError("Only active work can fail.", "STEP_NOT_ACTIVE", 409)
        error = self._required_text(error_summary, "Error summary", 2000)
        result = self._repository.apply_step_transition(
            user_id, run_id, step_id, [step["status"]], "failed", "step.failed",
            payload={"error": error}, error_summary=error,
            run_expected=[run["status"]], run_target="failed",
            run_event_type="run.failed",
            run_payload={"step_id": step_id, "error": error},
            run_error_summary=error,
        )
        if not result.get("changed"):
            code = "RUN_STATE_CONFLICT" if result.get("run_conflict") else "STEP_STATE_CONFLICT"
            raise TaskExecutionError("Execution changed before failure was saved.", code, 409)
        return self.get_run(user_id, run_id)

    def retry_step(self, user_id: str, run_id: str, step_id: str) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"failed"})
        step = self._find_step(run, step_id)
        if step["status"] != "failed":
            raise TaskExecutionError("Only a failed step can be retried.", "STEP_NOT_FAILED", 409)
        if int(step["attempt_count"]) >= int(step["max_attempts"]):
            raise TaskExecutionError("This step has no retry attempts remaining.", "STEP_ATTEMPTS_EXHAUSTED", 409)
        result = self._repository.apply_step_transition(
            user_id, run_id, step_id, ["failed"], "ready", "step.retry_scheduled",
            error_summary="", run_expected=["failed"], run_target="running",
            run_event_type="run.resumed_after_retry", run_error_summary="",
        )
        if not result.get("changed"):
            code = "RUN_STATE_CONFLICT" if result.get("run_conflict") else "STEP_STATE_CONFLICT"
            raise TaskExecutionError("Execution changed before retry was saved.", code, 409)
        return self.get_run(user_id, run_id)

    def request_approval(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running"})
        step = self._find_step(run, step_id)
        if step["status"] not in {"ready", "running"}:
            raise TaskExecutionError(
                "Approval can only pause ready or running work.", "STEP_APPROVAL_NOT_ALLOWED", 409
            )
        approval = self._repository.request_approval_transition(
            user_id, run_id, step_id, step["status"], self._mapping(request)
        )
        if approval is None:
            raise TaskExecutionError(
                "Execution changed before approval was requested.", "STEP_STATE_CONFLICT", 409
            )
        return {"approval": approval, "run": self.get_run(user_id, run_id)}

    def resolve_approval(
        self,
        user_id: str,
        approval_id: str,
        decision: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise TaskExecutionError("Decision must be approved or rejected.", "INVALID_APPROVAL_DECISION")
        approval = self._repository.get_approval(user_id, approval_id)
        if approval is None:
            raise TaskExecutionError("Approval not found.", "APPROVAL_NOT_FOUND", 404)
        if approval["status"] != "pending":
            raise TaskExecutionError("Approval has already been resolved.", "APPROVAL_ALREADY_RESOLVED", 409)
        run_id = self._repository.resolve_approval_transition(
            user_id, approval_id, decision, note
        )
        if run_id is None:
            raise TaskExecutionError(
                "Approval or execution state changed before the decision was saved.",
                "APPROVAL_STATE_CONFLICT",
                409,
            )
        return self.get_run(user_id, run_id)

    def start_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        run = self._require_run_status(user_id, run_id, {"running"})
        step = self._find_step(run, step_id)
        if step["status"] != "running":
            raise TaskExecutionError("Actions can only run inside a running step.", "STEP_NOT_RUNNING", 409)
        action = self._repository.create_action(
            user_id,
            run_id,
            step_id,
            {
                "action_type": self._optional_text(values.get("action_type"), 60) or step["kind"],
                "tool_name": self._optional_text(values.get("tool_name"), 200),
                "input_data": self._mapping(values.get("input_data")),
                "idempotency_key": self._optional_text(values.get("idempotency_key"), 200),
            },
        )
        action.pop("_created", None)
        return action

    def complete_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        action_id: str,
        *,
        status: str,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._find_step(self.get_run(user_id, run_id), step_id)
        if status not in {"completed", "failed", "cancelled", "confirmed", "revision_requested", "unavailable"}:
            raise TaskExecutionError("Invalid action result status.", "INVALID_ACTION_STATUS")
        if not self._repository.complete_action(
            user_id, run_id, step_id, action_id, status,
            output_data=output_data, error_summary=error_summary
        ):
            raise TaskExecutionError("Action not found or already finished.", "ACTION_STATE_CONFLICT", 409)
        return self.get_run(user_id, run_id)

    def list_events(self, user_id: str, run_id: str) -> Sequence[Dict[str, Any]]:
        self.get_run(user_id, run_id)
        return self._repository.list_events(user_id, run_id)

    def get_run_review(self, user_id: str, run_id: str) -> Dict[str, Any]:
        """Build a durable, read-only result view from canonical execution records."""
        run = self.get_run(user_id, run_id)
        events = list(self._repository.list_events(user_id, run_id))
        reflection = self._repository.get_run_review(user_id, run_id)
        rewards = list(self._repository.list_run_reward_settlements(user_id, run_id))
        artifacts = list(run.get("artifacts", []))
        steps = list(run.get("steps", []))
        approvals = list(run.get("approvals", []))
        artifact_titles = {
            title.casefold()
            for artifact in artifacts
            if (title := self._text(artifact.get("title"), 200))
        }
        expected_deliverables = []
        for step in steps:
            criteria = self._mapping(step.get("completion_criteria"))
            deliverables = criteria.get("deliverables", [])
            if not isinstance(deliverables, list):
                continue
            for raw_deliverable in deliverables:
                if isinstance(raw_deliverable, Mapping):
                    title = self._optional_text(
                        raw_deliverable.get("title") or raw_deliverable.get("name"), 200
                    )
                else:
                    title = self._optional_text(raw_deliverable, 200)
                if not title:
                    continue
                expected_deliverables.append({
                    "title": title,
                    "step_id": step.get("step_id"),
                    "step_title": step.get("title", ""),
                    "step_status": step.get("status", "pending"),
                    "recorded": title.casefold() in artifact_titles,
                })
        missing_deliverables = [
            item for item in expected_deliverables if not item["recorded"]
        ]
        incomplete_steps = [
            {"step_id": step.get("step_id"), "title": step.get("title", ""), "status": step.get("status", "pending")}
            for step in steps
            if step.get("status") not in SATISFIED_STEP_STATUSES
        ]
        pending_approvals = [
            approval for approval in approvals if approval.get("status") == "pending"
        ]
        resolved_approvals = [
            approval for approval in approvals if approval.get("status") != "pending"
        ]
        reward_totals = {
            "growth_points": sum(int(item.get("growth_points") or 0) for item in rewards),
            "settlements": len(rewards),
        }
        completion = {
            "ready": not incomplete_steps and not pending_approvals and not missing_deliverables,
            "step_count": len(steps),
            "satisfied_steps": len(steps) - len(incomplete_steps),
            "incomplete_steps": incomplete_steps,
            "pending_approvals": [
                {"approval_id": item.get("approval_id"), "step_id": item.get("step_id"), "summary": self._approval_summary(item)}
                for item in pending_approvals
            ],
            "deliverables": {
                "declared": expected_deliverables,
                "recorded": len(expected_deliverables) - len(missing_deliverables),
                "missing": missing_deliverables,
                "status": "not_declared" if not expected_deliverables else ("complete" if not missing_deliverables else "incomplete"),
            },
        }
        return {
            "run_id": run_id,
            "status": run.get("status"),
            "summary": {
                "objective": run.get("objective") or run.get("title") or "",
                "step_count": len(steps),
                "completed_steps": len([step for step in steps if step.get("status") in SATISFIED_STEP_STATUSES]),
                "artifact_count": len(artifacts),
                "approval_count": len(approvals),
                "resolved_approvals": len(resolved_approvals),
                "event_count": len(events),
            },
            "completion": completion,
            "artifacts": artifacts,
            "outputs": [
                {
                    "step_id": step.get("step_id"),
                    "step_title": step.get("title", ""),
                    "data": self._mapping(step.get("output_data")),
                }
                for step in steps
                if self._mapping(step.get("output_data"))
            ],
            "approvals": [
                {
                    "approval_id": item.get("approval_id"),
                    "step_id": item.get("step_id"),
                    "status": item.get("status"),
                    "summary": self._approval_summary(item),
                    "decision": self._mapping(item.get("decision_data")),
                    "resolved_at": item.get("resolved_at"),
                }
                for item in approvals
            ],
            "rewards": {"items": rewards, "totals": reward_totals},
            "reflection": reflection,
            "next_action": self._review_next_action(run, completion, reflection),
        }

    def update_run_review(
        self,
        user_id: str,
        run_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        run = self.get_run(user_id, run_id)
        if run.get("status") not in TERMINAL_RUN_STATUSES:
            raise TaskExecutionError(
                "Finish, cancel, or stop this action before writing its review.",
                "RUN_REVIEW_NOT_AVAILABLE",
                409,
            )
        existing = self._repository.get_run_review(user_id, run_id) or {}
        merged = {
            "outcome": existing.get("outcome"),
            "rating": existing.get("rating"),
            "notes": existing.get("notes", ""),
            "next_action": existing.get("next_action", ""),
        }
        for field, maximum in (("outcome", 30), ("notes", 4000), ("next_action", 1000)):
            if field in values:
                value = values.get(field)
                merged[field] = None if field == "outcome" and value is None else self._optional_text(value, maximum)
        if "rating" in values:
            rating = values.get("rating")
            merged["rating"] = None if rating is None else self._integer(rating, default=1, minimum=1, maximum=5)
        reflection = self._repository.upsert_run_review(user_id, run_id, merged)
        self._repository.append_event(
            user_id,
            run_id,
            "run.review_updated",
            payload={
                "outcome": reflection.get("outcome"),
                "rating": reflection.get("rating"),
                "has_notes": bool(reflection.get("notes")),
                "has_next_action": bool(reflection.get("next_action")),
            },
        )
        self._record_run_review_observation(user_id, run, reflection)
        self._propose_run_review_memory(user_id, run, reflection)
        return self.get_run_review(user_id, run_id)

    def _propose_run_review_memory(
        self,
        user_id: str,
        run: Mapping[str, Any],
        reflection: Mapping[str, Any],
    ) -> None:
        sink = self._run_review_memory_candidate_sink
        if sink is None:
            return
        try:
            sink.propose_run_review_memory(user_id, run, reflection)
        except Exception:
            # A saved review remains valid if optional memory suggestion capture fails.
            logger.exception("Unable to propose review memory for run_id=%s", run.get("run_id"))

    def _record_run_review_observation(
        self,
        user_id: str,
        run: Mapping[str, Any],
        reflection: Mapping[str, Any],
    ) -> None:
        sink = self._run_review_observation_sink
        if sink is None:
            return
        try:
            sink.record_run_review(user_id, run, reflection)
        except Exception:
            # A saved review remains valid even if optional evidence capture is unavailable.
            logger.exception("Unable to record run review evidence for run_id=%s", run.get("run_id"))

    @staticmethod
    def _approval_summary(approval: Mapping[str, Any]) -> str:
        request = approval.get("request_data")
        if isinstance(request, Mapping):
            value = request.get("summary")
            if isinstance(value, str) and value.strip():
                return value.strip()
        value = approval.get("summary")
        return value.strip() if isinstance(value, str) and value.strip() else "需要确认的事项"

    @staticmethod
    def _review_next_action(
        run: Mapping[str, Any],
        completion: Mapping[str, Any],
        reflection: Optional[Mapping[str, Any]],
    ) -> Dict[str, str]:
        if reflection and isinstance(reflection.get("next_action"), str) and reflection["next_action"].strip():
            return {"kind": "user_defined", "text": reflection["next_action"].strip()}
        if completion.get("pending_approvals"):
            return {"kind": "approval", "text": "先处理仍在等待的确认。"}
        deliverables = completion.get("deliverables") if isinstance(completion.get("deliverables"), Mapping) else {}
        if deliverables.get("missing"):
            return {"kind": "deliverable", "text": "补齐尚未记录的成果，再结束这次行动。"}
        if completion.get("incomplete_steps"):
            return {"kind": "step", "text": "完成或处理未结束的步骤。"}
        if run.get("status") == "completed":
            return {"kind": "follow_up", "text": "基于这次成果创建下一项行动。"}
        if run.get("status") == "failed":
            return {"kind": "recover", "text": "调整方案后，创建一次新的行动继续推进。"}
        if run.get("status") == "cancelled":
            return {"kind": "restart", "text": "保留这次记录，按新的条件重新开始。"}
        return {"kind": "continue", "text": "继续推进当前行动。"}

    def _require_run_status(
        self, user_id: str, run_id: str, allowed: set[str]
    ) -> Dict[str, Any]:
        run = self.get_run(user_id, run_id)
        if run["status"] not in allowed:
            raise TaskExecutionError(
                f"Run status {run['status']} does not allow this command.",
                "RUN_STATUS_CONFLICT",
                409,
            )
        return run

    @staticmethod
    def _find_step(run: Mapping[str, Any], step_id: str) -> Dict[str, Any]:
        for step in run.get("steps", []):
            if step.get("step_id") == step_id:
                return dict(step)
        raise TaskExecutionError("Step not found.", "STEP_NOT_FOUND", 404)

    @staticmethod
    def _has_approved_decision(run: Mapping[str, Any], step_id: str) -> bool:
        return any(
            approval.get("step_id") == step_id and approval.get("status") == "approved"
            for approval in run.get("approvals", [])
        )

    def _normalize_steps(self, raw_steps: Any) -> list[Dict[str, Any]]:
        if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
            raise TaskExecutionError("Run steps must be a list.", "RUN_STEPS_INVALID")
        if not raw_steps or len(raw_steps) > 100:
            raise TaskExecutionError("A run needs between 1 and 100 steps.", "RUN_STEP_COUNT_INVALID")
        normalized = []
        for position, raw in enumerate(raw_steps):
            if not isinstance(raw, Mapping):
                raise TaskExecutionError("Each step must be an object.", "RUN_STEP_INVALID")
            key = self._optional_text(raw.get("client_key"), 100) or f"step-{position + 1}"
            kind = self._choice(raw.get("kind") or "manual", STEP_KINDS, "step kind")
            max_attempts = self._integer(raw.get("max_attempts"), default=1, minimum=1, maximum=10)
            depends_on = raw.get("depends_on") or []
            if not isinstance(depends_on, Sequence) or isinstance(depends_on, (str, bytes)):
                raise TaskExecutionError("Step dependencies must be a list of step keys.", "STEP_DEPENDENCIES_INVALID")
            normalized.append({
                "client_key": key,
                "title": self._required_text(raw.get("title"), "Step title", 160),
                "description": self._text(raw.get("description"), 2000),
                "kind": kind,
                "depends_on": [str(item) for item in depends_on],
                "parallel_group": self._optional_text(raw.get("parallel_group"), 100),
                "max_attempts": max_attempts,
                "requires_approval": bool(raw.get("requires_approval")),
                "completion_criteria": self._mapping(raw.get("completion_criteria")),
                "input_data": self._mapping(raw.get("input_data")),
                "reward_spec": self._normalize_reward_spec(raw.get("reward_spec")),
            })
        return normalized

    @staticmethod
    def _validate_graph(steps: Sequence[Mapping[str, Any]]) -> None:
        keys = [str(step["client_key"]) for step in steps]
        if len(keys) != len(set(keys)):
            raise TaskExecutionError("Step keys must be unique within a run.", "DUPLICATE_STEP_KEY")
        graph = {str(step["client_key"]): [str(item) for item in step["depends_on"]] for step in steps}
        for key, dependencies in graph.items():
            for dependency in dependencies:
                if dependency not in graph:
                    raise TaskExecutionError(
                        f"Step {key} depends on unknown step {dependency}.", "UNKNOWN_STEP_DEPENDENCY"
                    )
                if dependency == key:
                    raise TaskExecutionError("A step cannot depend on itself.", "CYCLIC_STEP_DEPENDENCY")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visiting:
                raise TaskExecutionError("Step dependency graph contains a cycle.", "CYCLIC_STEP_DEPENDENCY")
            if key in visited:
                return
            visiting.add(key)
            for dependency in graph[key]:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in graph:
            visit(key)

    @staticmethod
    def _normalize_reward_spec(value: Any) -> Dict[str, int]:
        """Validate the fixed points amount that a completed Step may settle.

        This runs while a Run is created, before the specification reaches SQLite. It
        accepts no model-defined attributes or execution-time pricing and returns a
        compact JSON-safe mapping consumed by the repository completion transaction.
        """
        if value is None:
            reward: Dict[str, Any] = {}
        elif not isinstance(value, Mapping):
            raise TaskExecutionError(
                "Step rewards must be an object.", "STEP_REWARD_INVALID"
            )
        else:
            reward = dict(value)
        growth_points = reward.get("growth_points", 0)
        if isinstance(growth_points, bool) or not isinstance(growth_points, int):
            raise TaskExecutionError(
                "Step growth points must be an integer.", "STEP_REWARD_INVALID"
            )
        if not 0 <= growth_points <= 1000:
            raise TaskExecutionError(
                "Step growth points must be between 0 and 1000.", "STEP_REWARD_INVALID"
            )
        if set(reward) - {"growth_points"}:
            raise TaskExecutionError(
                "Step rewards may only declare growth_points.", "STEP_REWARD_INVALID"
            )
        return {"growth_points": growth_points}

    @staticmethod
    def _mapping(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TaskExecutionError("Expected an object value.", "INVALID_OBJECT_VALUE")
        return dict(value)

    def _normalize_artifacts(self, artifacts: Any) -> list[Dict[str, Any]]:
        """Normalize user evidence once for manual records and AI review submissions."""
        if artifacts is None:
            return []
        if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
            raise TaskExecutionError("Artifacts must be a list.", "INVALID_ARTIFACTS")
        return [
            {
                "title": self._required_text(item.get("title"), "Artifact title", 200),
                "kind": self._optional_text(item.get("kind"), 60) or "result",
                "uri": self._optional_text(item.get("uri"), 2000),
                "content_type": self._optional_text(item.get("content_type"), 200),
                "metadata": self._mapping(item.get("metadata")),
            }
            for item in artifacts
            if isinstance(item, Mapping)
        ]

    @staticmethod
    def _required_text(value: Any, label: str, maximum: int) -> str:
        text = str(value or "").strip()
        if not text:
            raise TaskExecutionError(f"{label} is required.", "REQUIRED_VALUE_MISSING")
        if len(text) > maximum:
            raise TaskExecutionError(f"{label} is too long.", "VALUE_TOO_LONG")
        return text

    @staticmethod
    def _text(value: Any, maximum: int) -> str:
        text = str(value or "").strip()
        if len(text) > maximum:
            raise TaskExecutionError("Text value is too long.", "VALUE_TOO_LONG")
        return text

    @staticmethod
    def _optional_text(value: Any, maximum: int) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        if len(text) > maximum:
            raise TaskExecutionError("Text value is too long.", "VALUE_TOO_LONG")
        return text

    @staticmethod
    def _choice(value: Any, allowed: Sequence[str], label: str) -> str:
        text = str(value)
        if text not in allowed:
            raise TaskExecutionError(f"Invalid {label}.", "INVALID_CHOICE")
        return text

    @staticmethod
    def _integer(value: Any, *, default: int, minimum: int, maximum: int) -> int:
        try:
            number = int(value if value is not None else default)
        except (TypeError, ValueError) as exc:
            raise TaskExecutionError("Expected an integer value.", "INVALID_INTEGER") from exc
        if number < minimum or number > maximum:
            raise TaskExecutionError("Integer value is outside the allowed range.", "INTEGER_OUT_OF_RANGE")
        return number

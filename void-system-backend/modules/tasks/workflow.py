"""Task lifecycle workflow with prerequisite and reward invariants."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from core.planning_contracts import EvaluationEngine, EvaluationRequest
from core.task_contracts import (
    CompletionResult, RewardGrant, TaskEvaluationOutcome, TaskRepository,
    TaskWorkflowError, VALID_TASK_STATUSES,
)


class TaskWorkflow:
    def __init__(self, repository: TaskRepository, evaluator: Optional[EvaluationEngine] = None) -> None:
        self._repository = repository
        self._evaluator = evaluator

    def change_status(self, user_id: str, task_id: str, target_status: str) -> CompletionResult:
        if target_status not in VALID_TASK_STATUSES:
            allowed = ", ".join(sorted(VALID_TASK_STATUSES))
            raise TaskWorkflowError(f"状态值无效。必须是: {allowed}", "INVALID_STATUS")
        task, tasks = self._load_task_context(user_id, task_id)
        if target_status == "in_progress":
            self._require_prerequisites(task, tasks, "无法开始任务。请先完成前置任务")
        if target_status == "completed":
            if task.get("status") == "completed":
                return CompletionResult(task_id, "completed", reward_granted=False)
            self._require_prerequisites(task, tasks, "请先完成前置任务再完成当前任务")
            self._require_completion_ready(task)
            reward = self._default_reward(task, self._repository.list_attributes(user_id))
            granted = self._repository.settle_completion(user_id, task_id, reward)
            return CompletionResult(task_id, "completed", granted, reward if granted else None)
        if not self._repository.update_status(user_id, task_id, target_status):
            raise TaskWorkflowError("任务状态更新失败", "TASK_STATUS_UPDATE_FAILED", 500)
        return CompletionResult(task_id, target_status, reward_granted=False)

    def submit_proof(self, user_id: str, task_id: str, proof: Dict[str, Any]) -> None:
        task, tasks = self._load_task_context(user_id, task_id)
        if task.get("status") == "completed":
            raise TaskWorkflowError("任务已完成，无法提交证明", "TASK_ALREADY_COMPLETED")
        self._require_prerequisites(task, tasks, "请先完成前置任务再提交证明")
        if not self._repository.submit_proof(user_id, task_id, proof):
            raise TaskWorkflowError("任务证明提交失败", "TASK_PROOF_SUBMIT_FAILED", 500)

    def record_evaluation(
        self, user_id: str, task_id: str, *,
        self_evaluation: Optional[Dict[str, Any]] = None,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> None:
        task, tasks = self._load_task_context(user_id, task_id)
        self._require_prerequisites(task, tasks, "请先完成前置任务再提交评估")
        if not self._repository.update_evaluation(
            user_id, task_id, self_evaluation=self_evaluation, ai_suggestion=ai_suggestion
        ):
            raise TaskWorkflowError("任务评估更新失败", "TASK_EVALUATION_UPDATE_FAILED", 500)

    def evaluate_submission(
        self, user_id: str, task_id: str, submission: str,
        media_urls: Optional[Sequence[str]] = None,
    ) -> TaskEvaluationOutcome:
        if self._evaluator is None:
            raise TaskWorkflowError("评估引擎未配置", "EVALUATION_ENGINE_UNAVAILABLE", 503)
        task, tasks = self._load_task_context(user_id, task_id)
        self._require_prerequisites(task, tasks, "请先完成前置任务再进行 AI 评估")
        attributes = self._repository.list_attributes(user_id)
        try:
            evaluated = self._evaluator.evaluate(EvaluationRequest(
                task=task,
                submission={"submission": submission, "media_urls": list(media_urls or [])},
                user_stats={"attributes": attributes},
            ))
            result = dict(evaluated.raw or {})
            result.setdefault("status", evaluated.status)
            result.setdefault("feedback", evaluated.feedback)
            result.setdefault("score", evaluated.score)
            result.setdefault("suggested_rewards", evaluated.suggested_rewards)
        except Exception as exc:
            raise TaskWorkflowError(
                "评估引擎暂时不可用，请稍后重试。", "EVALUATION_ENGINE_FAILED", 503
            ) from exc
        normalized = self._normalize_evaluation(result)
        suggestion = {
            "status": normalized.status,
            "feedback": normalized.feedback,
            "score": normalized.score,
        }
        if normalized.status == "pass" and task.get("status") != "completed":
            reward = self._evaluation_reward(task, attributes, normalized)
            suggestion["rewards"] = normalized.suggested_rewards
            granted = self._repository.settle_completion(
                user_id, task_id, reward, ai_suggestion=suggestion
            )
            return TaskEvaluationOutcome(
                normalized.status, normalized.feedback, normalized.score,
                normalized.suggested_rewards, granted, normalized.raw,
            )
        if not self._repository.update_evaluation(user_id, task_id, ai_suggestion=suggestion):
            raise TaskWorkflowError("AI 评估结果保存失败", "TASK_EVALUATION_UPDATE_FAILED", 500)
        return normalized

    def _load_task_context(self, user_id: str, task_id: str):
        tasks = list(self._repository.list_tasks(user_id))
        task = next((item for item in tasks if item.get("task_id") == task_id), None)
        if task is None:
            raise TaskWorkflowError("任务不存在或无权访问", "TASK_NOT_FOUND", 404)
        return task, tasks

    @staticmethod
    def _require_prerequisites(
        task: Mapping[str, Any], tasks: Iterable[Mapping[str, Any]], message_prefix: str
    ) -> None:
        prerequisites = list(task.get("prerequisites") or [])
        if not prerequisites:
            return
        task_list = list(tasks)
        completed = {item.get("task_id") for item in task_list if item.get("status") == "completed"}
        missing = [task_id for task_id in prerequisites if task_id not in completed]
        if not missing:
            return
        known = {item.get("task_id") for item in task_list}
        names = [str(item.get("task_name") or item.get("task_id")) for item in task_list if item.get("task_id") in missing]
        names.extend(task_id for task_id in missing if task_id not in known)
        raise TaskWorkflowError(f"{message_prefix}: {', '.join(names)}", "PREREQUISITES_NOT_MET")

    @staticmethod
    def _require_completion_ready(task: Mapping[str, Any]) -> None:
        completion_type = str(task.get("completion_type") or "simple")
        if completion_type == "ai_eval":
            raise TaskWorkflowError(
                "该任务需要提交 AI 评估，不能直接标记为完成",
                "TASK_EVALUATION_REQUIRED",
            )
        if completion_type == "progress" and TaskWorkflow._to_int(task.get("current_progress"), 0) < 100:
            raise TaskWorkflowError(
                "任务进度达到 100% 后才能完成",
                "TASK_PROGRESS_INCOMPLETE",
            )
        if completion_type == "submission" and not task.get("proof_data"):
            raise TaskWorkflowError(
                "请先提交完成证明",
                "TASK_PROOF_REQUIRED",
            )

    @classmethod
    def _default_reward(cls, task: Mapping[str, Any], attributes: Sequence[Mapping[str, Any]]) -> RewardGrant:
        coins = max(0, cls._to_int(task.get("reward_coins"), 10))
        return RewardGrant(
            coins, max(1, coins // 2), cls.calculate_attribute_rewards(task, attributes),
            f"task_{task.get('task_id')}_complete",
        )

    @classmethod
    def _evaluation_reward(
        cls, task: Mapping[str, Any], attributes: Sequence[Mapping[str, Any]],
        evaluation: TaskEvaluationOutcome,
    ) -> RewardGrant:
        suggested = evaluation.suggested_rewards
        coins = max(0, cls._to_int(suggested.get("coins"), cls._to_int(task.get("reward_coins"), 10)))
        known_ids = {str(attr.get("attr_id")) for attr in attributes if attr.get("attr_id")}
        increments = {
            str(attr_id): max(0, cls._to_int(value, 0))
            for attr_id, value in suggested.items()
            if attr_id != "coins" and str(attr_id) in known_ids and cls._to_int(value, 0) > 0
        }
        if not increments:
            increments = cls.calculate_attribute_rewards(task, attributes, max(0.1, evaluation.score / 100.0))
        return RewardGrant(coins, max(1, coins // 2), increments, f"ai_eval_task_{task.get('task_id')}")

    @staticmethod
    def _normalize_evaluation(result: Dict[str, Any]) -> TaskEvaluationOutcome:
        status = str(result.get("status") or "fail").lower()
        if status not in {"pass", "fail"}:
            status = "fail"
        feedback = str(result.get("feedback") or "评判结果异常，系统已降级处理。").strip()
        score = max(0, min(100, TaskWorkflow._to_int(result.get("score"), 0)))
        rewards = result.get("suggested_rewards")
        if not isinstance(rewards, dict):
            rewards = {}
        normalized_raw = dict(result)
        normalized_raw.update({"status": status, "feedback": feedback, "score": score, "suggested_rewards": rewards})
        return TaskEvaluationOutcome(status, feedback, score, dict(rewards), raw=normalized_raw)

    @staticmethod
    def calculate_attribute_rewards(
        task: Mapping[str, Any], attributes: Sequence[Mapping[str, Any]], score_factor: float = 1.0,
    ) -> Dict[str, int]:
        related = task.get("related_attrs") or {}
        if not isinstance(related, dict) or not related:
            return {}
        known_ids = {attr.get("attr_id") for attr in attributes if attr.get("attr_id")}
        weighted = [(str(attr_id), float(weight)) for attr_id, weight in related.items() if attr_id in known_ids and isinstance(weight, (int, float)) and weight > 0]
        total = int(max(0, round(TaskWorkflow._to_int(task.get("attribute_points"), 0) * max(0.1, score_factor))))
        if not weighted or total <= 0:
            return {}
        weight_sum = sum(weight for _, weight in weighted) or 1.0
        raw = [(attr_id, total * weight / weight_sum) for attr_id, weight in weighted]
        distribution = {attr_id: int(points) for attr_id, points in raw}
        remaining = total - sum(distribution.values())
        remainders = sorted(((points - int(points), attr_id) for attr_id, points in raw), reverse=True)
        for _, attr_id in remainders[:remaining]:
            distribution[attr_id] += 1
        return {attr_id: points for attr_id, points in distribution.items() if points > 0}

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

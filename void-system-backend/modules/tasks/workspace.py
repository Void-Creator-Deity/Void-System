"""Task workspace rules for user-created tasks, categories, and task chains."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.planning_contracts import PlanRequest, PlanningEngine, UserCapability
from core.task_contracts import TaskWorkflowError
from core.task_workspace_contracts import TaskWorkspaceError, TaskWorkspaceRepository
from modules.planning.context import build_generation_context
from modules.tasks.workflow import TaskWorkflow


@dataclass(frozen=True)
class TaskChainCreation:
    """Result of creating a task chain before asynchronous generation runs."""

    chain_id: str
    generation_status: str
    task_count: int = 0


class TaskWorkspace:
    """Own workspace-facing task, category, and chain rules behind one interface."""

    def __init__(
        self,
        repository: TaskWorkspaceRepository,
        workflow: TaskWorkflow,
        planner: Optional[PlanningEngine] = None,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self._planner = planner

    def list_categories(self, user_id: str) -> Sequence[Dict[str, Any]]:
        return self._repository.list_categories(user_id)

    def list_capabilities(self, user_id: str) -> List[Dict[str, Any]]:
        """Expose the current capabilities needed to plan generated workflow steps."""
        return self._repository.list_attributes(user_id)

    def create_category(self, user_id: str, values: Mapping[str, Any]) -> str:
        category_name = str(values.get("category_name") or "").strip()
        self._ensure_category_name_available(user_id, category_name)
        try:
            return self._repository.create_category(
                user_id,
                {
                    "category_name": category_name,
                    "description": str(values.get("description") or ""),
                    "icon": str(values.get("icon") or "\U0001f4da"),
                    "color": str(values.get("color") or "#3B82F6"),
                },
            )
        except Exception as exc:
            raise TaskWorkspaceError("任务分类创建失败", "CATEGORY_CREATE_FAILED", 500) from exc

    def update_category(
        self, user_id: str, category_id: str, values: Mapping[str, Any]
    ) -> None:
        self._require_category(user_id, category_id)
        updates = {key: value for key, value in values.items() if value is not None}
        if not updates:
            raise TaskWorkspaceError("请至少修改一项任务分类信息", "CATEGORY_UPDATE_EMPTY")
        if "category_name" in updates:
            updates["category_name"] = str(updates["category_name"]).strip()
            self._ensure_category_name_available(user_id, updates["category_name"], category_id)
        if not self._repository.update_category(user_id, category_id, updates):
            raise TaskWorkspaceError("任务分类更新失败", "CATEGORY_UPDATE_FAILED", 500)

    def delete_category(self, user_id: str, category_id: str) -> None:
        category = self._require_category(user_id, category_id)
        if bool(category.get("is_preset")):
            raise TaskWorkspaceError("预设任务分类不能删除", "CATEGORY_PRESET_PROTECTED")
        if not self._repository.delete_category(user_id, category_id):
            raise TaskWorkspaceError("任务分类删除失败", "CATEGORY_DELETE_FAILED", 500)

    def create_task(self, user_id: str, values: Mapping[str, Any]) -> str:
        category_id = self._optional_id(values.get("category_id"))
        chain_id = self._optional_id(values.get("chain_id"))
        if category_id:
            self._require_category(user_id, category_id, status_code=400)
        if chain_id and self._repository.get_chain(user_id, chain_id) is None:
            raise TaskWorkspaceError("任务流程不存在或无权访问", "TASK_CHAIN_NOT_FOUND")
        try:
            return self._repository.create_task(
                user_id,
                {
                    "task_name": str(values.get("task_name") or "").strip(),
                    "description": str(values.get("description") or ""),
                    "related_attrs": values.get("related_attrs") or {},
                    "estimated_time": self._to_int(values.get("estimated_time"), 30),
                    "reward_coins": self._to_int(values.get("reward_coins"), 10),
                    "priority": str(values.get("priority") or "medium"),
                    "attribute_points": self._to_int(values.get("attribute_points"), 0),
                    "category_id": category_id,
                    "chain_id": chain_id,
                    "chain_order": self._to_int(values.get("chain_order"), 0),
                    "prerequisites": list(values.get("prerequisites") or []),
                    "completion_type": str(values.get("completion_type") or "simple"),
                    "completion_criteria": values.get("completion_criteria") or {},
                    "task_type": str(values.get("task_type") or "main"),
                    "is_optional": bool(values.get("is_optional")),
                    "is_daily": bool(values.get("is_daily")),
                },
            )
        except TaskWorkspaceError:
            raise
        except Exception as exc:
            raise TaskWorkspaceError("任务创建失败，请稍后重试", "TASK_CREATE_FAILED", 500) from exc

    def list_tasks(
        self,
        user_id: str,
        *,
        task_status: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        tasks = self._repository.list_workspace_tasks(
            user_id,
            task_status=task_status,
            category_id=category_id,
            limit=limit,
            offset=offset,
        )
        return {
            "tasks": list(tasks),
            "stats": self._repository.task_statistics(user_id),
            "pagination": {"total": len(tasks), "limit": limit, "offset": offset},
        }

    def get_task(self, user_id: str, task_id: str) -> Dict[str, Any]:
        task = self._repository.get_workspace_task(user_id, task_id)
        if task is None:
            raise TaskWorkspaceError("任务不存在或无权访问", "TASK_NOT_FOUND", 404)
        return task

    def execution_link(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        return self._repository.get_execution_link(user_id, task_id)

    def chain_execution_link(self, user_id: str, chain_id: str) -> Optional[Dict[str, Any]]:
        return self._repository.get_chain_execution_link(user_id, chain_id)

    def legacy_execution_audit(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        return self._repository.legacy_execution_audit(user_id)

    def delete_task(self, user_id: str, task_id: str) -> None:
        if not self._repository.delete_workspace_task(user_id, task_id):
            raise TaskWorkspaceError("任务不存在或无权访问", "TASK_NOT_FOUND", 404)

    def update_task_progress(self, user_id: str, task_id: str, progress: int) -> bool:
        task = self.get_task(user_id, task_id)
        if not self._repository.update_task_progress(user_id, task_id, progress):
            raise TaskWorkspaceError("进度更新失败，请稍后重试", "TASK_PROGRESS_UPDATE_FAILED", 500)
        if progress != 100 or task.get("completion_type") != "progress":
            return False
        try:
            completion = self._workflow.change_status(user_id, task_id, "completed")
        except TaskWorkflowError as exc:
            raise TaskWorkspaceError(exc.message, exc.code, exc.status_code) from exc
        return completion.reward_granted

    def list_chains(self, user_id: str) -> Sequence[Dict[str, Any]]:
        return self._repository.list_chains(user_id)

    def create_chain(self, user_id: str, values: Mapping[str, Any]) -> TaskChainCreation:
        steps = values.get("steps")
        target_goal = self._optional_text(values.get("target_goal"))
        if steps and target_goal:
            raise TaskWorkspaceError(
                "请使用手动步骤或目标生成其中一种方式创建任务流程",
                "TASK_CHAIN_SOURCE_AMBIGUOUS",
            )
        chain_id = self._repository.create_chain(
            user_id,
            str(values.get("chain_name") or "").strip(),
            str(values.get("description") or ""),
            "queued" if target_goal else "ready",
        )
        if not steps:
            return TaskChainCreation(chain_id, "queued" if target_goal else "ready")
        try:
            normalized_steps = self._normalize_steps(steps, self._repository.list_attributes(user_id))
            task_ids = self._repository.create_chain_steps(user_id, chain_id, normalized_steps)
        except Exception as exc:
            self._repository.update_chain_generation(
                user_id, chain_id, "failed", "任务步骤未能保存，请删除后重新创建。"
            )
            raise TaskWorkspaceError("任务流程创建失败，请稍后重试", "TASK_CHAIN_CREATE_FAILED", 500) from exc
        return TaskChainCreation(chain_id, "ready", len(task_ids))

    def generate_chain_steps(
        self,
        user_id: str,
        chain_id: str,
        target_goal: str,
        user_profile: Mapping[str, Any],
    ) -> int:
        """Generate and persist a legacy chain through the Planning Engine seam."""
        if self._planner is None:
            raise TaskWorkspaceError(
                "Planning is not configured for this workspace.",
                "TASK_CHAIN_PLANNER_UNAVAILABLE",
                503,
            )
        self.mark_chain_generating(user_id, chain_id)
        raw_capabilities = self._repository.list_attributes(user_id)
        capabilities = [
            UserCapability(
                id=str(item.get("attr_id") or ""),
                name=str(item.get("attr_name") or ""),
                value=self._to_int(item.get("attr_value"), 0),
                max_value=self._to_int(item.get("max_value"), 100),
                description=str(item.get("description") or ""),
            )
            for item in raw_capabilities
            if item.get("attr_id")
        ]
        try:
            result = self._planner.plan(
                PlanRequest(
                    topic=str(target_goal).strip(),
                    profile_context=build_generation_context(
                        dict(user_profile), list(raw_capabilities)
                    ),
                    capabilities=capabilities,
                    mode="auto",
                    max_steps=50,
                    strict=True,
                )
            )
            return self.persist_generated_steps(
                user_id, chain_id, [asdict(task) for task in result.tasks]
            )
        except TaskWorkspaceError as exc:
            self.mark_chain_failed(user_id, chain_id, exc.message)
            raise
        except Exception as exc:
            message = "Planning is temporarily unavailable. Please retry later."
            self.mark_chain_failed(user_id, chain_id, message)
            raise TaskWorkspaceError(
                message, "TASK_CHAIN_GENERATION_FAILED", 503
            ) from exc

    def mark_chain_generating(self, user_id: str, chain_id: str) -> None:
        if not self._repository.update_chain_generation(user_id, chain_id, "generating"):
            raise TaskWorkspaceError("任务流程不存在或无权访问", "TASK_CHAIN_NOT_FOUND", 404)

    def persist_generated_steps(self, user_id: str, chain_id: str, raw_steps: Any) -> int:
        if not isinstance(raw_steps, list) or not raw_steps:
            raise TaskWorkspaceError("暂未生成可执行步骤，请调整目标后重试。", "TASK_CHAIN_EMPTY")
        normalized_steps = self._normalize_steps(raw_steps, self._repository.list_attributes(user_id))
        if not normalized_steps:
            raise TaskWorkspaceError("暂未生成可执行步骤，请调整目标后重试。", "TASK_CHAIN_EMPTY")
        try:
            return len(self._repository.create_chain_steps(user_id, chain_id, normalized_steps))
        except Exception as exc:
            raise TaskWorkspaceError("任务步骤未能保存，请删除后重新创建。", "TASK_CHAIN_CREATE_FAILED", 500) from exc

    def mark_chain_failed(self, user_id: str, chain_id: str, reason: str) -> None:
        self._repository.update_chain_generation(user_id, chain_id, "failed", reason)

    def delete_chain(self, user_id: str, chain_id: str) -> None:
        if not self._repository.delete_chain(user_id, chain_id):
            raise TaskWorkspaceError("任务流程不存在或无权访问", "TASK_CHAIN_NOT_FOUND", 404)

    def _require_category(
        self, user_id: str, category_id: str, status_code: int = 404
    ) -> Dict[str, Any]:
        category = self._repository.get_category(user_id, category_id)
        if category is None:
            raise TaskWorkspaceError("任务分类不存在或无权访问", "CATEGORY_NOT_FOUND", status_code)
        return category

    def _ensure_category_name_available(
        self, user_id: str, category_name: str, exclude_category_id: Optional[str] = None
    ) -> None:
        normalized = category_name.casefold()
        for category in self._repository.list_categories(user_id):
            if category.get("category_id") == exclude_category_id:
                continue
            if str(category.get("category_name") or "").strip().casefold() == normalized:
                raise TaskWorkspaceError("已有同名任务分类，请换一个名称", "CATEGORY_NAME_CONFLICT", 409)

    def _normalize_steps(
        self, steps: Sequence[Any], user_attrs: Sequence[Mapping[str, Any]]
    ) -> List[Dict[str, Any]]:
        return [
            self._normalize_workflow_step(step, user_attrs)
            for step in steps
            if isinstance(step, Mapping)
        ]

    @classmethod
    def _normalize_workflow_step(
        cls, step: Mapping[str, Any], user_attrs: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        title = str(step.get("title") or "").strip() or "待完成任务"
        description = str(step.get("description") or "").strip() or "请完成任务并提交可核验的结果。"
        reward_coins = max(0, min(1000, cls._to_int(step.get("reward_coins"), 20)))
        attribute_points = max(0, min(100, cls._to_int(step.get("attribute_points"), 5)))
        estimated_time = max(1, min(480, cls._to_int(step.get("estimated_time"), 30)))
        task_type = str(step.get("task_type") or "main")
        if task_type not in {"main", "side", "daily"}:
            task_type = "main"
        priority = str(step.get("priority") or "medium")
        if priority not in {"easy", "medium", "hard"}:
            priority = "medium"
        related_attrs = cls._normalize_related_attrs(step.get("related_attrs"), user_attrs)
        if not related_attrs and attribute_points > 0:
            related_attrs = cls._infer_related_attrs_from_task_text(step, user_attrs)
        completion_criteria = cls._completion_criteria(title, description, step.get("completion_criteria"))
        completion_criteria["attribute_plan"] = cls._attribute_plan(
            related_attrs, attribute_points, user_attrs
        )
        return {
            "title": title,
            "description": description,
            "related_attrs": related_attrs,
            "estimated_time": estimated_time,
            "reward_coins": reward_coins,
            "priority": priority,
            "attribute_points": attribute_points,
            "completion_type": str(step.get("completion_type") or "ai_eval"),
            "completion_criteria": completion_criteria,
            "task_type": task_type,
            "is_optional": bool(step.get("is_optional")),
            "is_daily": task_type == "daily",
        }

    @classmethod
    def _completion_criteria(
        cls, title: str, description: str, raw_criteria: Any
    ) -> Dict[str, Any]:
        defaults = cls._build_default_completion_criteria(title, description)
        if not isinstance(raw_criteria, Mapping) or not raw_criteria:
            return defaults
        return {key: raw_criteria.get(key) or value for key, value in defaults.items()}

    @staticmethod
    def _build_default_completion_criteria(title: str, description: str) -> Dict[str, Any]:
        return {
            "criteria": f"任务《{title}》需按要求完成并提供可核验依据。",
            "deliverables": ["执行过程说明", "最终结果总结"],
            "checks": [f"与任务描述一致：{description}", "说明关键步骤与结果"],
            "pass_threshold": "由评估服务按任务复杂度、证据完整度与结果质量综合判定",
            "evidence": ["截图", "代码片段", "日志记录", "总结复盘"],
        }

    @staticmethod
    def _normalize_related_attrs(
        raw_related: Any, user_attrs: Sequence[Mapping[str, Any]]
    ) -> Dict[str, float]:
        if not isinstance(raw_related, Mapping) or not raw_related:
            return {}
        attr_ids = {str(item.get("attr_id")) for item in user_attrs if item.get("attr_id")}
        attr_name_to_id = {
            str(item.get("attr_name") or "").strip().casefold(): str(item.get("attr_id"))
            for item in user_attrs
            if item.get("attr_id")
        }
        normalized: Dict[str, float] = {}
        for key, value in raw_related.items():
            if not isinstance(value, (int, float)):
                continue
            raw_key = str(key).strip()
            attribute_id = raw_key if raw_key in attr_ids else attr_name_to_id.get(raw_key.casefold())
            if attribute_id:
                normalized[attribute_id] = float(max(0.1, min(1.0, value)))
        return normalized

    @staticmethod
    def _infer_related_attrs_from_task_text(
        step: Mapping[str, Any], user_attrs: Sequence[Mapping[str, Any]]
    ) -> Dict[str, float]:
        text = " ".join((
            str(step.get("title") or "").strip().casefold(),
            str(step.get("description") or "").strip().casefold(),
        ))
        if not text.strip():
            return {}
        scored: List[tuple[str, float]] = []
        for attribute in user_attrs:
            attribute_id = str(attribute.get("attr_id") or "").strip()
            if not attribute_id:
                continue
            score = 0.0
            for candidate in (
                str(attribute.get("attr_name") or "").strip().casefold(),
                str(attribute.get("description") or "").strip().casefold(),
            ):
                if len(candidate) >= 2 and candidate in text:
                    score += min(1.0, len(candidate) / max(1, len(text)))
            if score > 0:
                scored.append((attribute_id, score))
        if not scored:
            return {}
        top = sorted(scored, key=lambda item: item[1], reverse=True)[:3]
        total = sum(score for _, score in top) or 1.0
        return {attribute_id: round(score / total, 3) for attribute_id, score in top}

    @staticmethod
    def _attribute_plan(
        related_attrs: Mapping[str, float], attribute_points: int, user_attrs: Sequence[Mapping[str, Any]]
    ) -> List[Dict[str, Any]]:
        distribution = TaskWorkflow.calculate_attribute_rewards(
            {"related_attrs": dict(related_attrs), "attribute_points": attribute_points}, user_attrs
        )
        names = {
            str(item.get("attr_id")): item.get("attr_name")
            for item in user_attrs
            if item.get("attr_id")
        }
        return [
            {
                "attr_id": attribute_id,
                "attr_name": names.get(attribute_id) or attribute_id,
                "points": points,
            }
            for attribute_id, points in distribution.items()
            if points > 0
        ]

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _optional_id(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _optional_text(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        return text or None

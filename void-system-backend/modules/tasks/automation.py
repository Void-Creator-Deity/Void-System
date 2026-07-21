"""Trigger-to-Run automation for creating user-owned Runs."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping, Optional, Sequence

from core.task_automation_contracts import TaskAutomationError, TaskAutomationRepository
from core.task_execution_contracts import TaskExecutionError
from modules.tasks.execution import TaskExecution


TRIGGER_TYPES = frozenset({"schedule", "event"})
TRIGGER_STATUSES = frozenset({"active", "paused"})


class TaskAutomation:
    """Own Trigger lifecycle behind one compact interface."""

    def __init__(self, repository: TaskAutomationRepository, execution: TaskExecution) -> None:
        self._repository = repository
        self._execution = execution

    def create_trigger(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        goal_id = self._required_text(values.get("goal_id"), "Goal", 200)
        trigger_type = self._choice(values.get("trigger_type"), TRIGGER_TYPES, "trigger type")
        configuration = self._configuration(trigger_type, values.get("configuration"))
        run_template = self._mapping(values.get("run_template"), "Run template")
        try:
            normalized_template = self._execution.validate_run_template(
                user_id, goal_id, run_template
            )
        except TaskExecutionError as exc:
            raise self._execution_error(exc) from exc
        normalized_template.pop("idempotency_key", None)
        return self._repository.create_trigger(
            user_id,
            {
                "goal_id": goal_id,
                "name": self._required_text(values.get("name"), "Trigger name", 160),
                "trigger_type": trigger_type,
                "configuration": configuration,
                "run_template": normalized_template,
            },
        )

    def list_triggers(self, user_id: str) -> Sequence[Dict[str, Any]]:
        return self._repository.list_triggers(user_id)

    def get_trigger(self, user_id: str, trigger_id: str) -> Dict[str, Any]:
        trigger = self._repository.get_trigger(user_id, trigger_id)
        if trigger is None:
            raise TaskAutomationError("Trigger not found.", "TRIGGER_NOT_FOUND", 404)
        return trigger

    def update_trigger(
        self, user_id: str, trigger_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        trigger = self.get_trigger(user_id, trigger_id)
        updates: Dict[str, Any] = {}
        if "name" in values:
            updates["name"] = self._required_text(values.get("name"), "Trigger name", 160)
        if "configuration" in values:
            updates["configuration"] = self._configuration(
                trigger["trigger_type"], values.get("configuration")
            )
        if "run_template" in values:
            template = self._mapping(values.get("run_template"), "Run template")
            try:
                normalized = self._execution.validate_run_template(
                    user_id, trigger["goal_id"], template
                )
            except TaskExecutionError as exc:
                raise self._execution_error(exc) from exc
            normalized.pop("idempotency_key", None)
            updates["run_template"] = normalized
        if not updates:
            return trigger
        if not self._repository.update_trigger(user_id, trigger_id, updates):
            raise TaskAutomationError("Trigger changed before it could be updated.", "TRIGGER_STATE_CONFLICT", 409)
        return self.get_trigger(user_id, trigger_id)

    def delete_trigger(self, user_id: str, trigger_id: str) -> None:
        self.get_trigger(user_id, trigger_id)
        if not self._repository.delete_trigger(user_id, trigger_id):
            raise TaskAutomationError("Trigger not found.", "TRIGGER_NOT_FOUND", 404)

    def pause_trigger(self, user_id: str, trigger_id: str) -> Dict[str, Any]:
        return self._set_trigger_status(user_id, trigger_id, "paused")

    def resume_trigger(self, user_id: str, trigger_id: str) -> Dict[str, Any]:
        return self._set_trigger_status(user_id, trigger_id, "active")

    def fire_trigger(
        self,
        user_id: str,
        trigger_id: str,
        source_key: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        trigger = self.get_trigger(user_id, trigger_id)
        normalized_source_key = self._required_text(source_key, "Trigger source key", 200)
        existing = self._repository.get_firing(
            user_id, trigger_id, normalized_source_key
        )
        if existing is not None:
            return {
                "trigger": trigger,
                "firing": existing,
                "run": self._get_run(user_id, existing["run_id"]),
            }
        if trigger["status"] != "active":
            raise TaskAutomationError(
                "Only active triggers can create a run.", "TRIGGER_NOT_ACTIVE", 409
            )

        run_values = dict(trigger["run_template"])
        metadata = dict(run_values.get("metadata") or {})
        metadata.update(
            {
                "trigger_id": trigger_id,
                "trigger_type": trigger["trigger_type"],
                "trigger_source_key": normalized_source_key,
            }
        )
        run_values["metadata"] = metadata
        source_digest = hashlib.sha256(normalized_source_key.encode("utf-8")).hexdigest()
        run_values["idempotency_key"] = f"trigger:{trigger_id}:{source_digest}"
        try:
            run = self._execution.create_run(
                user_id, trigger["goal_id"], run_values
            )
        except TaskExecutionError as exc:
            raise self._execution_error(exc) from exc

        normalized_payload = self._mapping(payload, "Trigger payload")
        firing = self._repository.record_firing(
            user_id,
            trigger_id,
            normalized_source_key,
            run["run_id"],
            normalized_payload,
        )
        return {
            "trigger": self.get_trigger(user_id, trigger_id),
            "firing": firing,
            "run": self._get_run(user_id, firing["run_id"]),
        }

    def _set_trigger_status(
        self, user_id: str, trigger_id: str, status: str
    ) -> Dict[str, Any]:
        trigger = self.get_trigger(user_id, trigger_id)
        if trigger["status"] == status:
            return trigger
        if not self._repository.set_trigger_status(
            user_id, trigger_id, status
        ):
            raise TaskAutomationError("Trigger not found.", "TRIGGER_NOT_FOUND", 404)
        return self.get_trigger(user_id, trigger_id)

    def _get_run(self, user_id: str, run_id: str) -> Dict[str, Any]:
        try:
            return self._execution.get_run(user_id, run_id)
        except TaskExecutionError as exc:
            raise self._execution_error(exc) from exc

    @staticmethod
    def _configuration(trigger_type: str, value: Any) -> Dict[str, Any]:
        configuration = TaskAutomation._mapping(value, "Trigger configuration")
        if trigger_type == "event":
            event_type = str(configuration.get("event_type") or "").strip()
            if not event_type or len(event_type) > 200:
                raise TaskAutomationError(
                    "Event triggers require an event_type.",
                    "TRIGGER_CONFIGURATION_INVALID",
                )
            configuration["event_type"] = event_type
            return configuration

        cron = str(configuration.get("cron") or "").strip()
        interval = configuration.get("interval_seconds")
        if cron:
            if len(cron) > 200:
                raise TaskAutomationError(
                    "Cron expression is too long.", "TRIGGER_CONFIGURATION_INVALID"
                )
            configuration["cron"] = cron
            return configuration
        try:
            seconds = int(interval)
        except (TypeError, ValueError) as exc:
            raise TaskAutomationError(
                "Schedule triggers require cron or interval_seconds.",
                "TRIGGER_CONFIGURATION_INVALID",
            ) from exc
        if seconds < 10 or seconds > 31_536_000:
            raise TaskAutomationError(
                "Trigger interval is outside the allowed range.",
                "TRIGGER_CONFIGURATION_INVALID",
            )
        configuration["interval_seconds"] = seconds
        return configuration

    @staticmethod
    def _mapping(value: Any, label: str) -> Dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TaskAutomationError(f"{label} must be an object.", "INVALID_OBJECT_VALUE")
        return dict(value)

    @staticmethod
    def _required_text(value: Any, label: str, maximum: int) -> str:
        text = str(value or "").strip()
        if not text:
            raise TaskAutomationError(f"{label} is required.", "REQUIRED_VALUE_MISSING")
        if len(text) > maximum:
            raise TaskAutomationError(f"{label} is too long.", "VALUE_TOO_LONG")
        return text

    @staticmethod
    def _optional_text(value: Any, maximum: int) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        if len(text) > maximum:
            raise TaskAutomationError("Text value is too long.", "VALUE_TOO_LONG")
        return text

    @staticmethod
    def _choice(value: Any, allowed: Sequence[str], label: str) -> str:
        text = str(value or "")
        if text not in allowed:
            raise TaskAutomationError(f"Invalid {label}.", "INVALID_CHOICE")
        return text

    @staticmethod
    def _execution_error(exc: TaskExecutionError) -> TaskAutomationError:
        return TaskAutomationError(exc.message, exc.code, exc.status_code)

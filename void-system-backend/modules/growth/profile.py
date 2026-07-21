"""Growth Profile module for capabilities and reward read models."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

from core.growth_contracts import GrowthProfileError, GrowthProfileRepository


class GrowthProfile:
    def __init__(self, repository: GrowthProfileRepository) -> None:
        self._repository = repository

    def balance(self, user_id: str) -> int:
        return self._repository.get_balance(user_id)

    def growth_point_activity(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        return self._repository.list_growth_point_activity(user_id, limit)

    def growth_point_summary(self, user_id: str) -> Dict[str, Any]:
        return self._repository.growth_point_summary(user_id)

    def list_capabilities(self, user_id: str) -> List[Dict[str, Any]]:
        return self._repository.list_attributes(user_id)

    def create_capability(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        name = str(values.get("attr_name") or "").strip()
        self._ensure_name_available(user_id, name)
        try:
            attr_id = self._repository.create_attribute(
                user_id,
                {
                    "attr_name": name,
                    "max_value": int(values.get("max_value") or 100),
                    "description": str(values.get("description") or ""),
                    "icon": str(values.get("icon") or "\U0001f4ca"),
                },
            )
        except Exception as exc:
            raise GrowthProfileError("Growth attribute could not be created", "ATTRIBUTE_CREATE_FAILED", 500) from exc
        return self._require_capability(user_id, attr_id)

    def update_capability(
        self, user_id: str, attr_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        current = self._require_capability(user_id, attr_id)
        updates = {key: value for key, value in values.items() if value is not None}
        if "attr_name" in updates:
            updates["attr_name"] = str(updates["attr_name"]).strip()
            if updates["attr_name"].casefold() != str(current["attr_name"]).casefold():
                self._ensure_name_available(user_id, updates["attr_name"], attr_id)
        maximum = int(updates.get("max_value") or current["max_value"])
        if "attr_value" in updates:
            updates["attr_value"] = min(int(updates["attr_value"]), maximum)
        elif "max_value" in updates and int(current["attr_value"]) > maximum:
            updates["attr_value"] = maximum
        if not updates:
            raise GrowthProfileError("Growth attribute could not be updated", "ATTRIBUTE_UPDATE_FAILED", 500)
        if not self._repository.update_attribute(user_id, attr_id, updates):
            raise GrowthProfileError("Growth attribute could not be updated", "ATTRIBUTE_UPDATE_FAILED", 500)
        return self._require_capability(user_id, attr_id)

    def delete_capability(self, user_id: str, attr_id: str) -> None:
        self._require_capability(user_id, attr_id)
        if not self._repository.delete_attribute(user_id, attr_id):
            raise GrowthProfileError("Growth attribute could not be deleted", "ATTRIBUTE_DELETE_FAILED", 500)

    def _require_capability(self, user_id: str, attr_id: str) -> Dict[str, Any]:
        attribute = self._repository.get_attribute(user_id, attr_id)
        if attribute is None:
            raise GrowthProfileError("Growth attribute was not found", "ATTRIBUTE_NOT_FOUND", 404)
        return attribute

    def _ensure_name_available(self, user_id: str, name: str, exclude_attr_id: str | None = None) -> None:
        normalized = name.casefold()
        for attribute in self._repository.list_attributes(user_id):
            if attribute.get("attr_id") == exclude_attr_id:
                continue
            if str(attribute.get("attr_name") or "").strip().casefold() == normalized:
                raise GrowthProfileError("Attribute name already exists", "ATTRIBUTE_EXISTS")

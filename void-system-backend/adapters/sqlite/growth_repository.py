"""SQLite adapter for a user's capabilities and reward activity."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from adapters.sqlite.connection import ConnectionFactory
from core.growth_contracts import GrowthProfileRepository


class SQLiteGrowthProfileRepository(GrowthProfileRepository):
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_balance(self, user_id: str) -> int:
        conn = self._connection_factory()
        try:
            row = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM growth_point_ledger WHERE user_id = ?", (user_id,)).fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()

    def list_growth_point_activity(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM growth_point_ledger WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def growth_point_summary(self, user_id: str) -> Dict[str, Any]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_income,
                       COALESCE(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 0) AS total_expense,
                       COALESCE(SUM(CASE WHEN amount > 0 AND created_at >= date('now', '-7 days') THEN amount ELSE 0 END), 0) AS weekly_income,
                       COALESCE(ABS(SUM(CASE WHEN amount < 0 AND created_at >= date('now', '-7 days') THEN amount ELSE 0 END)), 0) AS weekly_expense
                   FROM growth_point_ledger WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            total_income = int(row["total_income"] or 0)
            total_expense = int(row["total_expense"] or 0)
            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "weekly_income": int(row["weekly_income"] or 0),
                "weekly_expense": int(row["weekly_expense"] or 0),
                "net_income": total_income - total_expense,
            }
        finally:
            conn.close()

    def list_attributes(self, user_id: str) -> List[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_attribute(self, user_id: str, attr_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                "SELECT * FROM attributes WHERE attr_id = ? AND user_id = ?", (attr_id, user_id)
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def create_attribute(self, user_id: str, values: Mapping[str, Any]) -> str:
        attr_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO attributes
                   (attr_id, user_id, attr_name, max_value, description, icon, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    attr_id,
                    user_id,
                    str(values["attr_name"]),
                    int(values.get("max_value") or 100),
                    str(values.get("description") or ""),
                    str(values.get("icon") or "\U0001f4ca"),
                    now,
                    now,
                ),
            )
            conn.commit()
            return attr_id
        finally:
            conn.close()

    def update_attribute(self, user_id: str, attr_id: str, values: Mapping[str, Any]) -> bool:
        fields = ("attr_name", "attr_value", "description", "max_value")
        updates = [(field, values[field]) for field in fields if field in values]
        if not updates:
            return False
        assignments = [f"{field} = ?" for field, _ in updates]
        parameters: List[Any] = [value for _, value in updates]
        assignments.append("updated_at = ?")
        parameters.extend((datetime.now().isoformat(), attr_id, user_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE attributes SET {', '.join(assignments)} WHERE attr_id = ? AND user_id = ?",
                parameters,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_attribute(self, user_id: str, attr_id: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                "DELETE FROM attributes WHERE attr_id = ? AND user_id = ?", (attr_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

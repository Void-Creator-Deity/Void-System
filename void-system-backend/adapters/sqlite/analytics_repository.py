"""SQLite read-model adapter for administrator analytics."""
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Dict, List


class SQLiteAnalyticsRepository:
    """Keeps aggregate SQL out of HTTP routes and returns stable empty-safe shapes."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]):
        self._connection_factory = connection_factory

    def _one(self, query: str, parameters: tuple[Any, ...] = ()) -> Dict[str, Any]:
        connection = self._connection_factory()
        try:
            row = connection.execute(query, parameters).fetchone()
            return dict(row) if row else {}
        finally:
            connection.close()

    def _many(self, query: str, parameters: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]
        finally:
            connection.close()

    @staticmethod
    def _cutoff(days: int) -> str:
        return f"-{max(1, min(days, 365))} days"

    def user_overview(self, user_id: str) -> Dict[str, Any]:
        """Return one user dashboard overview without currency semantics."""
        connection = self._connection_factory()
        try:
            attributes = [dict(row) for row in connection.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()]
            user_row = connection.execute(
                """SELECT COUNT(*) AS total_tasks,
                          COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_tasks,
                          COALESCE(SUM(CASE WHEN status IN ('ready', 'running', 'waiting_approval') THEN 1 ELSE 0 END), 0) AS in_progress_tasks
                   FROM task_steps WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            total_tasks = int(user_row["total_tasks"] or 0)
            completed_tasks = int(user_row["completed_tasks"] or 0)
            growth_points = int(connection.execute(
                """SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)
                   FROM growth_point_ledger WHERE user_id = ?""",
                (user_id,),
            ).fetchone()[0] or 0)
            recent_growth_points = int(connection.execute(
                """SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)
                   FROM growth_point_ledger
                   WHERE user_id = ? AND created_at >= date('now', '-7 days')""",
                (user_id,),
            ).fetchone()[0] or 0)
            user_stats = {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": int(user_row["in_progress_tasks"] or 0),
                "completion_rate": completed_tasks / total_tasks * 100 if total_tasks else 0,
                "growth_points": growth_points,
                "total_documents": int(connection.execute(
                    "SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,)
                ).fetchone()[0] or 0),
            }
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM task_steps WHERE user_id = ? GROUP BY status", (user_id,)
            ).fetchall()
            task_stats = {
                "total_tasks": sum(int(row["count"]) for row in status_rows),
                "status_stats": {str(row["status"]): int(row["count"]) for row in status_rows},
                "completed_last_30_days": int(connection.execute(
                    """SELECT COUNT(*) FROM task_steps WHERE user_id = ? AND status = 'completed'
                       AND completed_at >= date('now', '-30 days')""", (user_id,)
                ).fetchone()[0] or 0),
                "avg_estimated_time": round(float(connection.execute(
                    """SELECT COALESCE(AVG((julianday(completed_at) - julianday(created_at)) * 24), 0)
                       FROM task_steps WHERE user_id = ? AND status = 'completed' AND completed_at IS NOT NULL""", (user_id,)
                ).fetchone()[0] or 0), 1),
            }
            values = [int(attribute.get("attr_value") or 0) for attribute in attributes]
            return {
                "user_stats": user_stats,
                "task_stats": task_stats,
                "attribute_stats": {
                    "total_attributes": len(attributes),
                    "average_value": sum(values) / len(values) if values else 0,
                    "max_value_attr": max(attributes, key=lambda item: int(item.get("attr_value") or 0)) if attributes else None,
                },
                "growth_points": {
                    "total_recorded": growth_points,
                    "recorded_last_7_days": recent_growth_points,
                },
            }
        finally:
            connection.close()

    def global_user_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS total_users,
                      SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) AS admin_users,
                      SUM(CASE WHEN last_login IS NOT NULL THEN 1 ELSE 0 END) AS users_with_login,
                      SUM(CASE WHEN datetime(created_at) >= datetime('now', '-30 days') THEN 1 ELSE 0 END) AS new_users_30d
                 FROM users"""
        )

    def global_task_stats(self) -> Dict[str, Any]:
        result = self._one(
            """SELECT COUNT(*) AS total_tasks,
                      COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_tasks,
                      COALESCE(SUM(CASE WHEN status IN ('ready', 'running', 'waiting_approval') THEN 1 ELSE 0 END), 0) AS in_progress_tasks,
                      COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) AS pending_tasks
                 FROM task_steps"""
        )
        total = int(result.get("total_tasks") or 0)
        completed = int(result.get("completed_tasks") or 0)
        result["completion_rate"] = completed / total * 100 if total else 0
        return result

    def global_attribute_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS total_attributes,
                      COALESCE(SUM(attr_value), 0) AS total_value,
                      COALESCE(AVG(attr_value), 0) AS average_value
                 FROM attributes"""
        )

    def global_growth_point_stats(self) -> Dict[str, Any]:
        """Aggregate recorded points without treating them as spendable balances."""
        return self._one(
            """WITH point_totals AS (
                    SELECT user_id, COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS recorded_points
                    FROM growth_point_ledger GROUP BY user_id
                )
                SELECT COALESCE((SELECT SUM(recorded_points) FROM point_totals), 0) AS total_recorded_points,
                       COALESCE((SELECT COUNT(*) FROM point_totals WHERE recorded_points > 0), 0) AS users_with_recorded_points,
                       COALESCE((SELECT AVG(recorded_points) FROM point_totals WHERE recorded_points > 0), 0) AS average_recorded_points,
                       COALESCE((SELECT COUNT(*) FROM growth_point_ledger WHERE amount > 0), 0) AS recorded_activity_count"""
        )

    def global_document_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS total_documents,
                      SUM(CASE WHEN parse_status = 'completed' THEN 1 ELSE 0 END) AS ready_documents,
                      SUM(CASE WHEN parse_status IN ('pending', 'processing') THEN 1 ELSE 0 END) AS processing_documents,
                      SUM(CASE WHEN parse_status = 'failed' THEN 1 ELSE 0 END) AS failed_documents
                 FROM user_documents"""
        )

    def user_registration_trend(self, days: int) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS user_count
                 FROM users WHERE datetime(created_at) >= datetime('now', ?)
                 GROUP BY substr(created_at, 1, 10) ORDER BY date""",
            (self._cutoff(days),),
        )

    def user_activity_stats(self, days: int) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS total_users,
                      SUM(CASE WHEN datetime(last_login) >= datetime('now', ?) THEN 1 ELSE 0 END) AS active_users,
                      SUM(CASE WHEN last_login IS NULL THEN 1 ELSE 0 END) AS never_logged_in
                 FROM users""",
            (self._cutoff(days),),
        )

    def user_level_distribution(self) -> List[Dict[str, Any]]:
        return self._many(
            "SELECT level, COUNT(*) AS user_count FROM users GROUP BY level ORDER BY level"
        )

    def task_status_distribution(self) -> List[Dict[str, Any]]:
        return self._many(
            "SELECT status, COUNT(*) AS task_count FROM task_steps GROUP BY status ORDER BY status"
        )

    def task_completion_trend(self, days: int) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT substr(completed_at, 1, 10) AS date, COUNT(*) AS completed_count
                 FROM task_steps
                 WHERE status = 'completed' AND completed_at IS NOT NULL
                   AND datetime(completed_at) >= datetime('now', ?)
                 GROUP BY substr(completed_at, 1, 10) ORDER BY date""",
            (self._cutoff(days),),
        )

    def task_category_stats(self) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT kind AS category_name, kind AS category_id, COUNT(*) AS task_count,
                      COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_count
                 FROM task_steps
                 GROUP BY kind
                 ORDER BY task_count DESC, category_name"""
        )

    def task_duration_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS completed_tasks,
                      COALESCE(AVG((julianday(completed_at) - julianday(created_at)) * 24), 0) AS average_completion_hours
                 FROM task_steps
                 WHERE status = 'completed' AND completed_at IS NOT NULL"""
        )

    def attribute_type_distribution(self) -> List[Dict[str, Any]]:
        return self._many(
            "SELECT attr_name, COUNT(*) AS attribute_count FROM attributes GROUP BY attr_name ORDER BY attribute_count DESC, attr_name"
        )

    def attribute_value_distribution(self) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT CASE
                        WHEN attr_value < 20 THEN '0-19'
                        WHEN attr_value < 40 THEN '20-39'
                        WHEN attr_value < 60 THEN '40-59'
                        WHEN attr_value < 80 THEN '60-79'
                        ELSE '80-100+'
                      END AS value_range,
                      COUNT(*) AS attribute_count
                 FROM attributes GROUP BY value_range
                 ORDER BY CASE value_range
                    WHEN '0-19' THEN 1 WHEN '20-39' THEN 2 WHEN '40-59' THEN 3
                    WHEN '60-79' THEN 4 ELSE 5 END"""
        )

    def popular_attributes(self, limit: int) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT attr_name, COUNT(*) AS attribute_count,
                      COALESCE(AVG(attr_value), 0) AS average_value
                 FROM attributes GROUP BY attr_name
                 ORDER BY attribute_count DESC, average_value DESC, attr_name LIMIT ?""",
            (max(1, min(limit, 100)),),
        )

    def growth_point_activity_trend(self, days: int) -> List[Dict[str, Any]]:
        """Return daily positive point records for the requested analytics window."""
        return self._many(
            """SELECT substr(created_at, 1, 10) AS date,
                      COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS recorded_points,
                      COALESCE(SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END), 0) AS activity_count
                 FROM growth_point_ledger
                 WHERE datetime(created_at) >= datetime(?)
                 GROUP BY substr(created_at, 1, 10) ORDER BY date""",
            (self._cutoff(days),),
        )

    def growth_point_distribution(self) -> List[Dict[str, Any]]:
        """Group users by recorded points; historical debits never create negative bands."""
        return self._many(
            """WITH recorded_points AS (
                    SELECT u.user_id, COALESCE(SUM(CASE WHEN ledger.amount > 0 THEN ledger.amount ELSE 0 END), 0) AS total_points
                    FROM users u
                    LEFT JOIN growth_point_ledger ledger ON ledger.user_id = u.user_id
                    GROUP BY u.user_id
                )
                SELECT CASE
                        WHEN total_points = 0 THEN '0'
                        WHEN total_points < 100 THEN '1-99'
                        WHEN total_points < 500 THEN '100-499'
                        WHEN total_points < 1000 THEN '500-999'
                        ELSE '1000+'
                      END AS points_range,
                      COUNT(*) AS user_count
                 FROM recorded_points GROUP BY points_range
                 ORDER BY CASE points_range
                    WHEN '0' THEN 1 WHEN '1-99' THEN 2 WHEN '100-499' THEN 3
                    WHEN '500-999' THEN 4 ELSE 5 END"""
        )

    def growth_point_health_metrics(self) -> Dict[str, Any]:
        """Summarize recorded point activity for administrators."""
        return self._one(
            """WITH recorded_points AS (
                    SELECT u.user_id, COALESCE(SUM(CASE WHEN ledger.amount > 0 THEN ledger.amount ELSE 0 END), 0) AS total_points
                    FROM users u
                    LEFT JOIN growth_point_ledger ledger ON ledger.user_id = u.user_id
                    GROUP BY u.user_id
                )
                SELECT COUNT(*) AS total_users,
                       COALESCE(SUM(CASE WHEN total_points > 0 THEN 1 ELSE 0 END), 0) AS users_with_recorded_points,
                       COALESCE(AVG(total_points), 0) AS average_recorded_points
                  FROM recorded_points"""
        )

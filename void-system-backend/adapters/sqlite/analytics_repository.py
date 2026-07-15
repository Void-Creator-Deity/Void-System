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
        """Return the legacy dashboard shape with all per-user aggregation in one adapter."""
        connection = self._connection_factory()
        try:
            attributes = [dict(row) for row in connection.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()]
            user_row = connection.execute(
                """SELECT COUNT(*) AS total_tasks,
                          SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_tasks,
                          SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_tasks
                   FROM tasks WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            total_tasks = int(user_row["total_tasks"] or 0)
            completed_tasks = int(user_row["completed_tasks"] or 0)
            user_stats = {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": int(user_row["in_progress_tasks"] or 0),
                "completion_rate": completed_tasks / total_tasks * 100 if total_tasks else 0,
                "total_experience": int(connection.execute("SELECT COALESCE(SUM(amount), 0) FROM experience WHERE user_id = ?", (user_id,)).fetchone()[0] or 0),
                "total_earned_coins": int(connection.execute("SELECT COALESCE(SUM(amount), 0) FROM coins WHERE user_id = ? AND amount > 0", (user_id,)).fetchone()[0] or 0),
                "total_spent_coins": int(connection.execute("SELECT COALESCE(ABS(SUM(amount)), 0) FROM coins WHERE user_id = ? AND amount < 0", (user_id,)).fetchone()[0] or 0),
                "total_documents": int(connection.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,)).fetchone()[0] or 0),
            }
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM tasks WHERE user_id = ? GROUP BY status", (user_id,)
            ).fetchall()
            task_stats = {
                "total_tasks": sum(int(row["count"]) for row in status_rows),
                "status_stats": {str(row["status"]): int(row["count"]) for row in status_rows},
                "completed_last_30_days": int(connection.execute(
                    """SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'
                       AND completed_at >= date('now', '-30 days')""", (user_id,)
                ).fetchone()[0] or 0),
                "avg_estimated_time": round(float(connection.execute(
                    "SELECT COALESCE(AVG(estimated_time), 0) FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,)
                ).fetchone()[0] or 0), 1),
            }
            total_income = int(connection.execute("SELECT COALESCE(SUM(amount), 0) FROM coins WHERE user_id = ? AND amount > 0", (user_id,)).fetchone()[0] or 0)
            total_expense = int(connection.execute("SELECT COALESCE(ABS(SUM(amount)), 0) FROM coins WHERE user_id = ? AND amount < 0", (user_id,)).fetchone()[0] or 0)
            weekly_income = int(connection.execute("SELECT COALESCE(SUM(amount), 0) FROM coins WHERE user_id = ? AND amount > 0 AND created_at >= date('now', '-7 days')", (user_id,)).fetchone()[0] or 0)
            weekly_expense = int(connection.execute("SELECT COALESCE(ABS(SUM(amount)), 0) FROM coins WHERE user_id = ? AND amount < 0 AND created_at >= date('now', '-7 days')", (user_id,)).fetchone()[0] or 0)
            values = [int(attribute.get("attr_value") or 0) for attribute in attributes]
            return {
                "user_stats": user_stats,
                "task_stats": task_stats,
                "attribute_stats": {
                    "total_attributes": len(attributes),
                    "average_value": sum(values) / len(values) if values else 0,
                    "max_value_attr": max(attributes, key=lambda item: int(item.get("attr_value") or 0)) if attributes else None,
                },
                "income_expense": {
                    "total_income": total_income, "total_expense": total_expense,
                    "weekly_income": weekly_income, "weekly_expense": weekly_expense,
                    "net_income": total_income - total_expense,
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
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_tasks,
                      SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_tasks,
                      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_tasks
                 FROM tasks"""
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

    def global_economy_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT
                COALESCE((SELECT SUM(amount) FROM coins), 0) AS total_balance,
                COALESCE((SELECT SUM(amount) FROM coins WHERE amount > 0), 0) AS total_earned,
                COALESCE((SELECT ABS(SUM(amount)) FROM coins WHERE amount < 0), 0) AS total_spent,
                COALESCE((SELECT COUNT(*) FROM coins), 0) AS total_transactions,
                COALESCE((SELECT SUM(total_price) FROM purchase_history), 0) AS shop_revenue"""
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
            "SELECT status, COUNT(*) AS task_count FROM tasks GROUP BY status ORDER BY status"
        )

    def task_completion_trend(self, days: int) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT substr(completed_at, 1, 10) AS date, COUNT(*) AS completed_count
                 FROM tasks
                 WHERE status = 'completed' AND completed_at IS NOT NULL
                   AND datetime(completed_at) >= datetime('now', ?)
                 GROUP BY substr(completed_at, 1, 10) ORDER BY date""",
            (self._cutoff(days),),
        )

    def task_category_stats(self) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT COALESCE(c.category_name, 'Uncategorized') AS category_name,
                      t.category_id, COUNT(*) AS task_count,
                      SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                 FROM tasks t LEFT JOIN task_categories c ON c.category_id = t.category_id
                 GROUP BY t.category_id, c.category_name
                 ORDER BY task_count DESC, category_name"""
        )

    def task_duration_stats(self) -> Dict[str, Any]:
        return self._one(
            """SELECT COUNT(*) AS completed_tasks,
                      COALESCE(AVG((julianday(completed_at) - julianday(created_at)) * 24), 0) AS average_completion_hours
                 FROM tasks
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

    def coin_transaction_trend(self, days: int) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT substr(created_at, 1, 10) AS date,
                      COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS earned,
                      COALESCE(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 0) AS spent,
                      COALESCE(SUM(amount), 0) AS net
                 FROM coins WHERE datetime(created_at) >= datetime('now', ?)
                 GROUP BY substr(created_at, 1, 10) ORDER BY date""",
            (self._cutoff(days),),
        )

    def user_balance_distribution(self) -> List[Dict[str, Any]]:
        return self._many(
            """WITH balances AS (
                    SELECT u.user_id, COALESCE(SUM(c.amount), 0) AS balance
                    FROM users u LEFT JOIN coins c ON c.user_id = u.user_id GROUP BY u.user_id
                 )
                 SELECT CASE
                        WHEN balance < 0 THEN 'negative'
                        WHEN balance < 100 THEN '0-99'
                        WHEN balance < 500 THEN '100-499'
                        WHEN balance < 1000 THEN '500-999'
                        ELSE '1000+'
                      END AS balance_range,
                      COUNT(*) AS user_count
                 FROM balances GROUP BY balance_range
                 ORDER BY CASE balance_range
                    WHEN 'negative' THEN 1 WHEN '0-99' THEN 2 WHEN '100-499' THEN 3
                    WHEN '500-999' THEN 4 ELSE 5 END"""
        )

    def item_sales_stats(self) -> List[Dict[str, Any]]:
        return self._many(
            """SELECT item_id, item_name, SUM(quantity) AS total_quantity,
                      SUM(total_price) AS total_revenue
                 FROM purchase_history GROUP BY item_id, item_name
                 ORDER BY total_revenue DESC, item_name"""
        )

    def economy_health_metrics(self) -> Dict[str, Any]:
        return self._one(
            """WITH balances AS (
                    SELECT u.user_id, COALESCE(SUM(c.amount), 0) AS balance
                    FROM users u LEFT JOIN coins c ON c.user_id = u.user_id GROUP BY u.user_id
                 )
                 SELECT COUNT(*) AS users_with_balance,
                        COALESCE(AVG(balance), 0) AS average_balance,
                        SUM(CASE WHEN balance < 0 THEN 1 ELSE 0 END) AS negative_balance_users,
                        COALESCE((SELECT COUNT(*) FROM purchase_history), 0) AS total_purchases
                 FROM balances"""
        )

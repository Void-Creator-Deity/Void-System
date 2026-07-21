"""HTTP contract tests for Goal and Run execution."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from api.http.dependencies import get_task_execution
from adapters.sqlite.task_execution_repository import SQLiteTaskExecutionRepository
from core.planning_contracts import EvaluationResult
from modules.tasks.execution import TaskExecution


class _PassingEvaluationEngine:
    """Deterministic evaluator used to exercise the assisted HTTP contract."""

    def evaluate(self, _request):
        return EvaluationResult(
            status="pass",
            feedback="The submitted evidence meets the completion criteria.",
            score=92,
        )


class TaskExecutionHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            ApplicationOptions(
                database_path=str(Path(self.temp_dir.name) / "task-execution-http.db"),
                enable_ai_routes=False,
                enable_langserve_routes=False,
                bootstrap_admin=False,
            )
        )
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.app.dependency_overrides[get_task_execution] = lambda: TaskExecution(
            SQLiteTaskExecutionRepository(self.app.state.database.get_connection),
            evaluation_engine=_PassingEvaluationEngine(),
        )
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "execution@example.com",
                "username": "execution",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login",
            json={"identifier": "execution", "password": "secure-password-2026"},
        )
        self.assertEqual(logged_in.status_code, 200)
        self.headers = {
            "Authorization": f"Bearer {logged_in.json()['data']['access_token']}"
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_goal_run_step_and_event_contract(self) -> None:
        goal_response = self.client.post(
            "/api/goals",
            headers=self.headers,
            json={"title": "Ship a reliable release", "priority": "high"},
        )
        self.assertEqual(goal_response.status_code, 200)
        goal_id = goal_response.json()["data"]["goal"]["goal_id"]

        run_response = self.client.post(
            f"/api/goals/{goal_id}/runs",
            headers=self.headers,
            json={
                "mode": "manual",
                "steps": [
                    {"client_key": "prepare", "title": "Prepare"},
                    {
                        "client_key": "verify",
                        "title": "Verify",
                        "depends_on": ["prepare"],
                    },
                ],
            },
        )
        self.assertEqual(run_response.status_code, 200)
        run = run_response.json()["data"]["run"]
        run_id = run["run_id"]

        started = self.client.post(f"/api/runs/{run_id}/start", headers=self.headers)
        self.assertEqual(started.status_code, 200)
        run = started.json()["data"]["run"]
        prepare = next(step for step in run["steps"] if step["client_key"] == "prepare")
        verify = next(step for step in run["steps"] if step["client_key"] == "verify")
        self.assertEqual(prepare["status"], "ready")
        self.assertEqual(verify["status"], "pending")

        step_started = self.client.post(
            f"/api/runs/{run_id}/steps/{prepare['step_id']}/start",
            headers=self.headers,
        )
        self.assertEqual(step_started.status_code, 200)
        completed = self.client.post(
            f"/api/runs/{run_id}/steps/{prepare['step_id']}/complete",
            headers=self.headers,
            json={
                "output_data": {"result": "prepared"},
                "artifacts": [
                    {
                        "title": "Release notes",
                        "kind": "document",
                        "uri": "memory://release-notes",
                    }
                ],
            },
        )
        self.assertEqual(completed.status_code, 200)
        run = completed.json()["data"]["run"]
        verify = next(step for step in run["steps"] if step["client_key"] == "verify")
        self.assertEqual(verify["status"], "ready")
        self.assertEqual(len(run["artifacts"]), 1)

        events = self.client.get(f"/api/runs/{run_id}/events", headers=self.headers)
        self.assertEqual(events.status_code, 200)
        event_types = [item["event_type"] for item in events.json()["data"]["events"]]
        self.assertIn("run.started", event_types)
        self.assertIn("step.completed", event_types)

    def test_goal_creation_is_idempotent_per_owner(self) -> None:
        payload = {
            "title": "Publish a recoverable plan",
            "idempotency_key": "plan-goal-draft-001",
        }
        first = self.client.post("/api/goals", headers=self.headers, json=payload)
        retried = self.client.post("/api/goals", headers=self.headers, json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(retried.status_code, 200)
        first_goal = first.json()["data"]["goal"]
        retried_goal = retried.json()["data"]["goal"]
        self.assertEqual(first_goal["goal_id"], retried_goal["goal_id"])
        self.assertEqual(first_goal["idempotency_key"], payload["idempotency_key"])

        listed = self.client.get("/api/goals", headers=self.headers)
        matching = [
            goal for goal in listed.json()["data"]["goals"]
            if goal.get("idempotency_key") == payload["idempotency_key"]
        ]
        self.assertEqual(len(matching), 1)

    def test_goal_idempotency_key_is_isolated_by_owner(self) -> None:
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "other-execution@example.com",
                "username": "other-execution",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login",
            json={
                "identifier": "other-execution",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(logged_in.status_code, 200)
        other_headers = {
            "Authorization": f"Bearer {logged_in.json()['data']['access_token']}"
        }
        payload = {"title": "Owner scoped goal", "idempotency_key": "shared-key"}

        first_owner = self.client.post("/api/goals", headers=self.headers, json=payload)
        second_owner = self.client.post("/api/goals", headers=other_headers, json=payload)

        self.assertEqual(first_owner.status_code, 200)
        self.assertEqual(second_owner.status_code, 200)
        self.assertNotEqual(
            first_owner.json()["data"]["goal"]["goal_id"],
            second_owner.json()["data"]["goal"]["goal_id"],
        )

    def test_invalid_dependency_is_rejected_as_domain_error(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Invalid graph"}
        ).json()["data"]["goal"]
        response = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "steps": [
                    {"client_key": "only", "title": "Only", "depends_on": ["missing"]}
                ]
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "UNKNOWN_STEP_DEPENDENCY")

    def test_assisted_run_requires_evidence_and_retires_worker_leases(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Research architecture"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "mode": "assisted",
                "steps": [{"title": "Inspect modules"}],
            },
        ).json()["data"]["run"]
        step = self.client.post(
            f"/api/runs/{run['run_id']}/start", headers=self.headers
        ).json()["data"]["run"]["steps"][0]
        self.assertEqual(
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start",
                headers=self.headers,
            ).status_code,
            200,
        )
        blocked = self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/complete",
            headers=self.headers,
            json={},
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["error_code"], "ASSISTED_REVIEW_REQUIRED")
        reviewed = self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/review",
            headers=self.headers,
            json={
                "submission": "Inspected the relevant modules and recorded the outcome.",
                "idempotency_key": "inspection-review-1",
            },
        )
        self.assertEqual(reviewed.status_code, 200)
        completed_run = reviewed.json()["data"]["run"]
        self.assertEqual(completed_run["status"], "completed")
        self.assertEqual(completed_run["actions"][0]["status"], "confirmed")
        retired = self.client.post(
            f"/api/runs/{run['run_id']}/lease/release",
            headers=self.headers,
            json={},
        )
        self.assertEqual(retired.status_code, 404)

    def test_failed_run_can_resume_from_a_retryable_step(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Recover an interrupted action"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "steps": [
                    {"client_key": "recover", "title": "Recover work", "max_attempts": 2}
                ]
            },
        ).json()["data"]["run"]
        run = self.client.post(
            f"/api/runs/{run['run_id']}/start", headers=self.headers
        ).json()["data"]["run"]
        step = run["steps"][0]
        self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start",
            headers=self.headers,
        )
        failed = self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/fail",
            headers=self.headers,
            json={"error_summary": "Network access was interrupted"},
        )
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["data"]["run"]["status"], "failed")

        retried = self.client.post(
            f"/api/runs/{run['run_id']}/retry", headers=self.headers
        )
        self.assertEqual(retried.status_code, 200)
        recovered = retried.json()["data"]["run"]
        self.assertEqual(recovered["status"], "running")
        self.assertEqual(recovered["steps"][0]["status"], "ready")

        repeated = self.client.post(
            f"/api/runs/{run['run_id']}/retry", headers=self.headers
        )
        self.assertEqual(repeated.status_code, 409)
        stable = self.client.get(f"/api/runs/{run['run_id']}", headers=self.headers)
        self.assertEqual(stable.json()["data"]["run"]["status"], "running")
        self.assertEqual(stable.json()["data"]["run"]["steps"][0]["status"], "ready")

    def test_completed_run_review_summarizes_canonical_evidence(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Ship a reviewed result"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "objective": "Publish a concise release note",
                "steps": [{
                    "client_key": "publish",
                    "title": "Publish release note",
                    "completion_criteria": {"deliverables": ["Release note"]},
                }],
            },
        ).json()["data"]["run"]
        run_id = run["run_id"]
        started = self.client.post(f"/api/runs/{run_id}/start", headers=self.headers)
        self.assertEqual(started.status_code, 200)
        step = started.json()["data"]["run"]["steps"][0]
        self.assertEqual(
            self.client.post(
                f"/api/runs/{run_id}/steps/{step['step_id']}/start", headers=self.headers
            ).status_code,
            200,
        )
        finished = self.client.post(
            f"/api/runs/{run_id}/steps/{step['step_id']}/complete",
            headers=self.headers,
            json={
                "output_data": {"summary": "Release note is ready"},
                "artifacts": [{
                    "title": "Release note",
                    "kind": "document",
                    "uri": "https://example.test/release-note",
                }],
            },
        )
        self.assertEqual(finished.status_code, 200)
        self.assertEqual(finished.json()["data"]["run"]["status"], "completed")

        review = self.client.get(f"/api/runs/{run_id}/review", headers=self.headers)
        self.assertEqual(review.status_code, 200)
        data = review.json()["data"]["review"]
        self.assertTrue(data["completion"]["ready"])
        self.assertEqual(data["completion"]["deliverables"]["status"], "complete")
        self.assertEqual(data["summary"]["artifact_count"], 1)
        self.assertEqual(data["outputs"][0]["data"]["summary"], "Release note is ready")
        self.assertEqual(data["next_action"]["kind"], "follow_up")

        saved = self.client.put(
            f"/api/runs/{run_id}/review",
            headers=self.headers,
            json={
                "outcome": "met",
                "rating": 5,
                "notes": "The result was clear.",
                "next_action": "Turn the note into a reusable template.",
            },
        )
        self.assertEqual(saved.status_code, 200)
        persisted = saved.json()["data"]["review"]
        self.assertEqual(persisted["reflection"]["rating"], 5)
        self.assertEqual(persisted["next_action"]["kind"], "user_defined")
        self.assertEqual(
            persisted["next_action"]["text"], "Turn the note into a reusable template."
        )

        revised = self.client.put(
            f"/api/runs/{run_id}/review",
            headers=self.headers,
            json={"rating": 4},
        )
        self.assertEqual(revised.status_code, 200)
        refreshed = self.client.get(f"/api/runs/{run_id}/review", headers=self.headers)
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["data"]["review"]["reflection"]["outcome"], "met")
        events = self.client.get(f"/api/runs/{run_id}/events", headers=self.headers)
        self.assertIn(
            "run.review_updated",
            [event["event_type"] for event in events.json()["data"]["events"]],
        )

    def test_review_is_unavailable_until_the_run_reaches_a_terminal_state(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Review timing"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={"steps": [{"title": "Keep working"}]},
        ).json()["data"]["run"]
        response = self.client.put(
            f"/api/runs/{run['run_id']}/review",
            headers=self.headers,
            json={"notes": "Too early"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error_code"], "RUN_REVIEW_NOT_AVAILABLE")

    def test_goal_update_and_step_skip_contract(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Publish handbook"}
        ).json()["data"]["goal"]
        updated = self.client.patch(
            f"/api/goals/{goal['goal_id']}",
            headers=self.headers,
            json={"title": "Publish team handbook", "priority": "high"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["goal"]["priority"], "high")

        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={"steps": [{"client_key": "draft", "title": "Draft"}]},
        ).json()["data"]["run"]
        run = self.client.post(
            f"/api/runs/{run['run_id']}/start", headers=self.headers
        ).json()["data"]["run"]
        step = run["steps"][0]
        skipped = self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/skip",
            headers=self.headers,
        )
        self.assertEqual(skipped.status_code, 200)
        skipped_run = skipped.json()["data"]["run"]
        self.assertEqual(skipped_run["steps"][0]["status"], "skipped")
        self.assertEqual(skipped_run["status"], "completed")

        completed_goal = self.client.patch(
            f"/api/goals/{goal['goal_id']}",
            headers=self.headers,
            json={"status": "completed"},
        )
        self.assertEqual(completed_goal.status_code, 200)
        self.assertEqual(completed_goal.json()["data"]["goal"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()

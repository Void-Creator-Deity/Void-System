"""HTTP contract tests for Trigger-to-Run automation and Run commands."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class TaskAutomationHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(Path(self.temp_dir.name) / "automation-http.db"),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                )
            )
        )
        self.client.__enter__()
        self.headers = self._register_and_login(
            "automation", "automation@example.com"
        )
        self.other_headers = self._register_and_login(
            "automation-other", "automation-other@example.com"
        )

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def _register_and_login(self, username: str, email: str) -> dict:
        password = "secure-password-2026"
        registered = self.client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login",
            json={"identifier": username, "password": password},
        )
        self.assertEqual(logged_in.status_code, 200)
        return {
            "Authorization": f"Bearer {logged_in.json()['data']['access_token']}"
        }

    def _create_trigger(self) -> dict:
        goal = self.client.post(
            "/api/goals",
            headers=self.headers,
            json={"title": "Maintain release notes"},
        ).json()["data"]["goal"]
        response = self.client.post(
            "/api/triggers",
            headers=self.headers,
            json={
                "goal_id": goal["goal_id"],
                "name": "Release completed",
                "trigger_type": "event",
                "configuration": {"event_type": "release.completed"},
                "run_template": {
                    "mode": "agent",
                    "steps": [
                        {
                            "client_key": "draft",
                            "title": "Draft release notes",
                            "kind": "agent",
                        },
                        {
                            "client_key": "review",
                            "title": "Review release notes",
                            "kind": "review",
                            "depends_on": ["draft"],
                        },
                    ],
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["trigger"]

    def test_trigger_lifecycle_fire_and_command_contract(self) -> None:
        trigger = self._create_trigger()
        listed = self.client.get("/api/triggers", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            listed.json()["data"]["triggers"][0]["trigger_id"],
            trigger["trigger_id"],
        )

        first = self.client.post(
            f"/api/triggers/{trigger['trigger_id']}/fire",
            headers=self.headers,
            json={"source_key": "release:42", "payload": {"release": 42}},
        )
        duplicate = self.client.post(
            f"/api/triggers/{trigger['trigger_id']}/fire",
            headers=self.headers,
            json={"source_key": "release:42", "payload": {"release": 42}},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        run = first.json()["data"]["run"]
        self.assertEqual(
            run["run_id"], duplicate.json()["data"]["run"]["run_id"]
        )
        self.assertEqual(
            [item["client_key"] for item in run["steps"][1]["depends_on"]],
            ["draft"],
        )

        created_command = self.client.post(
            f"/api/runs/{run['run_id']}/commands",
            headers=self.headers,
            json={
                "command_type": "instruction",
                "instruction": "Mention the database migration.",
                "idempotency_key": "migration-note",
            },
        )
        repeated_command = self.client.post(
            f"/api/runs/{run['run_id']}/commands",
            headers=self.headers,
            json={
                "command_type": "instruction",
                "instruction": "Mention the database migration.",
                "idempotency_key": "migration-note",
            },
        )
        self.assertEqual(created_command.status_code, 200)
        command = created_command.json()["data"]["command"]
        self.assertEqual(
            command["command_id"],
            repeated_command.json()["data"]["command"]["command_id"],
        )
        pending = self.client.get(
            f"/api/runs/{run['run_id']}/commands?status=pending",
            headers=self.headers,
        )
        self.assertEqual(len(pending.json()["data"]["commands"]), 1)
        acknowledged = self.client.post(
            f"/api/runs/{run['run_id']}/commands/{command['command_id']}/acknowledge",
            headers=self.headers,
        )
        self.assertEqual(acknowledged.status_code, 200)
        self.assertEqual(
            acknowledged.json()["data"]["command"]["status"], "acknowledged"
        )

    def test_pause_and_owner_isolation_contract(self) -> None:
        trigger = self._create_trigger()
        hidden = self.client.get(
            f"/api/triggers/{trigger['trigger_id']}", headers=self.other_headers
        )
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json()["error_code"], "TRIGGER_NOT_FOUND")

        paused = self.client.post(
            f"/api/triggers/{trigger['trigger_id']}/pause", headers=self.headers
        )
        self.assertEqual(paused.status_code, 200)
        rejected = self.client.post(
            f"/api/triggers/{trigger['trigger_id']}/fire",
            headers=self.headers,
            json={"source_key": "paused-source"},
        )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["error_code"], "TRIGGER_NOT_ACTIVE")
        resumed = self.client.post(
            f"/api/triggers/{trigger['trigger_id']}/resume", headers=self.headers
        )
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()["data"]["trigger"]["status"], "active")

    def test_invalid_schedule_configuration_is_a_domain_error(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Scheduled review"}
        ).json()["data"]["goal"]
        response = self.client.post(
            "/api/triggers",
            headers=self.headers,
            json={
                "goal_id": goal["goal_id"],
                "name": "Broken schedule",
                "trigger_type": "schedule",
                "configuration": {},
                "run_template": {"steps": [{"title": "Review"}]},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error_code"], "TRIGGER_CONFIGURATION_INVALID"
        )

    def test_trigger_update_and_delete_contract(self) -> None:
        trigger = self._create_trigger()
        updated = self.client.patch(
            f"/api/triggers/{trigger['trigger_id']}",
            headers=self.headers,
            json={
                "name": "Updated release review",
                "configuration": {"event_type": "release.updated"},
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["data"]["trigger"]["configuration"]["event_type"],
            "release.updated",
        )
        deleted = self.client.delete(
            f"/api/triggers/{trigger['trigger_id']}", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 200)
        missing = self.client.get(
            f"/api/triggers/{trigger['trigger_id']}", headers=self.headers
        )
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()

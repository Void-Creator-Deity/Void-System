"""HTTP contract tests for Personal Context and the system companion."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository

from api.http.application import ApplicationOptions, create_app


class PersonalContextHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(Path(self.temp_dir.name) / "personal-context-http.db"),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                )
            )
        )
        self.client.__enter__()
        self.headers = self._register_and_login("owner", "owner@example.com")
        self.other_headers = self._register_and_login("other", "other@example.com")

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def _register_and_login(self, username: str, email: str) -> dict[str, str]:
        password = "secure-password-2026"
        registered = self.client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login", json={"identifier": username, "password": password}
        )
        self.assertEqual(logged_in.status_code, 200)
        return {"Authorization": f"Bearer {logged_in.json()['data']['access_token']}"}

    def _enable_profile_analysis(self, headers: dict[str, str]) -> None:
        response = self.client.put(
            "/api/companion/settings",
            headers=headers,
            json={"permissions": {"profile": True}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["settings"]["permissions"]["profile"])

    def _owner_id(self, username: str) -> str:
        connection = self.client.app.state.database.get_connection()
        try:
            row = connection.execute(
                "SELECT user_id FROM users WHERE username = ?", (username,)
            ).fetchone()
            self.assertIsNotNone(row)
            return str(row["user_id"])
        finally:
            connection.close()

    def test_default_permissions_can_be_changed_and_are_enforced(self) -> None:
        response = self.client.get("/api/companion/settings", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        settings = response.json()["data"]["settings"]
        self.assertTrue(settings["permissions"]["goals"])
        self.assertFalse(settings["permissions"]["profile"])
        self.assertFalse(settings["permissions"]["knowledge"])
        self.assertFalse(settings["permissions"]["rewards"])

        updated = self.client.put(
            "/api/companion/settings",
            headers=self.headers,
            json={
                "tone": "warm",
                "initiative": "proactive",
                "permissions": {"goals": False, "rewards": True},
            },
        )
        self.assertEqual(updated.status_code, 200)
        settings = updated.json()["data"]["settings"]
        self.assertEqual(settings["tone"], "warm")
        self.assertFalse(settings["permissions"]["goals"])
        self.assertTrue(settings["permissions"]["rewards"])

        context = self.client.get(
            "/api/companion/context?sections=goals&sections=rewards",
            headers=self.headers,
        )
        self.assertEqual(context.status_code, 200)
        snapshot = context.json()["data"]["context"]
        self.assertNotIn("goals", snapshot["included_sections"])
        self.assertIn("rewards", snapshot["included_sections"])
        self.assertEqual(snapshot["item_count"], 1)

    def test_expired_memory_remains_visible_but_never_enters_context(self) -> None:
        created = self.client.post(
            "/api/companion/memories",
            headers=self.headers,
            json={
                "memory_type": "preference",
                "title": "Temporary focus",
                "content": "Only relevant for a short planning window.",
                "expires_at": "2026-07-15T00:00:00+00:00",
            },
        )
        self.assertEqual(created.status_code, 200)
        memory = created.json()["data"]["memory"]
        memory_id = memory["memory_id"]
        self.assertEqual(memory["expires_at"], "2026-07-15T00:00:00+00:00")

        listed = self.client.get("/api/companion/memories", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertIn(memory_id, [item["memory_id"] for item in listed.json()["data"]["memories"]])

        expired_context = self.client.get(
            "/api/companion/context?sections=memories", headers=self.headers
        )
        self.assertEqual(expired_context.status_code, 200)
        self.assertEqual(expired_context.json()["data"]["context"]["sections"]["memories"], [])

        renewed = self.client.patch(
            f"/api/companion/memories/{memory_id}",
            headers=self.headers,
            json={"expires_at": "2026-12-31T23:59:59+00:00"},
        )
        self.assertEqual(renewed.status_code, 200)
        self.assertEqual(renewed.json()["data"]["memory"]["expires_at"], "2026-12-31T23:59:59+00:00")

        renewed_context = self.client.get(
            "/api/companion/context?sections=memories", headers=self.headers
        )
        self.assertEqual(renewed_context.status_code, 200)
        items = renewed_context.json()["data"]["context"]["sections"]["memories"]
        self.assertEqual([item["reference"]["id"] for item in items], [memory_id])

    def test_memory_crud_is_owner_scoped_and_preserves_type(self) -> None:
        created = self.client.post(
            "/api/companion/memories",
            headers=self.headers,
            json={
                "memory_type": "inference",
                "title": "Prefers short planning sessions",
                "content": "Observed across three completed weekly reviews.",
                "source_type": "run_evaluation",
                "source_ref": "weekly-review-series",
                "confidence": 0.72,
            },
        )
        self.assertEqual(created.status_code, 200)
        memory = created.json()["data"]["memory"]
        memory_id = memory["memory_id"]
        self.assertEqual(memory["memory_type"], "inference")
        self.assertAlmostEqual(memory["confidence"], 0.72)

        denied = self.client.patch(
            f"/api/companion/memories/{memory_id}",
            headers=self.other_headers,
            json={"title": "Changed"},
        )
        self.assertEqual(denied.status_code, 404)

        archived = self.client.patch(
            f"/api/companion/memories/{memory_id}",
            headers=self.headers,
            json={"status": "archived", "use_in_context": False},
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["data"]["memory"]["status"], "archived")

        filtered = self.client.get(
            "/api/companion/memories?status=archived&memory_type=inference",
            headers=self.headers,
        )
        self.assertEqual(len(filtered.json()["data"]["memories"]), 1)
        deleted = self.client.delete(
            f"/api/companion/memories/{memory_id}", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 200)

    def test_briefing_uses_goals_runs_and_records_explainable_access(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Publish a project demo"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "title": "Prepare demo release",
                "mode": "assisted",
                "steps": [{"client_key": "prepare", "title": "Prepare demo"}],
            },
        ).json()["data"]["run"]

        briefing_response = self.client.get(
            "/api/companion/briefing?item_budget=8", headers=self.headers
        )
        self.assertEqual(briefing_response.status_code, 200)
        briefing = briefing_response.json()["data"]["briefing"]
        self.assertEqual(briefing["focus_items"][0]["reference"]["id"], run["run_id"])
        self.assertEqual(briefing["suggestions"][0]["kind"], "start_run")
        self.assertIn("goals", briefing["context"]["included_sections"])
        self.assertIn("runs", briefing["context"]["included_sections"])
        self.assertTrue(briefing["context"]["audit_id"])

        access_log = self.client.get(
            "/api/companion/access-log", headers=self.headers
        )
        self.assertEqual(access_log.status_code, 200)
        records = access_log.json()["data"]["records"]
        self.assertEqual(records[0]["purpose"], "companion_briefing")
        self.assertIn("goals", records[0]["included_sections"])

        other_log = self.client.get(
            "/api/companion/access-log", headers=self.other_headers
        ).json()["data"]["records"]
        self.assertEqual(other_log, [])


    def test_context_audit_explains_permissions_and_budget(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Finish an explainable context"}
        ).json()["data"]["goal"]
        created_memory = self.client.post(
            "/api/companion/memories",
            headers=self.headers,
            json={
                "memory_type": "preference",
                "title": "Keep the response concise",
                "content": "Prefer a short summary before implementation details.",
            },
        )
        self.assertEqual(created_memory.status_code, 200)
        response = self.client.get(
            "/api/companion/context?sections=goals&sections=memories&sections=knowledge&item_budget=1",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        context = response.json()["data"]["context"]
        self.assertEqual(context["item_count"], 1)
        self.assertEqual(len(context["selected_references"]), 1)
        self.assertIn("selection", context["sections"]["goals"][0])
        sources = {item["section"]: item for item in context["sources"]}
        self.assertEqual(sources["knowledge"]["decision"], "excluded")
        self.assertFalse(sources["knowledge"]["permission"])
        self.assertTrue(sources["memories"]["truncated"])
        self.assertIn(
            {"section": "knowledge", "reason": "permission"},
            context["omitted_sections"],
        )
        self.assertIn(
            {"section": "memories", "reason": "budget"},
            context["omitted_sections"],
        )

        audit = self.client.get("/api/companion/access-log", headers=self.headers)
        self.assertEqual(audit.status_code, 200)
        record = audit.json()["data"]["records"][0]
        self.assertEqual(record["item_count"], 1)
        self.assertEqual(len(record["selected_references"]), 1)
        recorded_sources = {item["section"]: item for item in record["source_decisions"]}
        self.assertEqual(recorded_sources["knowledge"]["reason"], "Not enabled in companion settings.")
        self.assertIn({"section": "memories", "reason": "budget"}, record["omitted_sections"])
        self.assertEqual(goal["title"], "Finish an explainable context")

    def test_task_review_memory_candidate_requires_confirmation_before_context_use(self) -> None:
        goal_response = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Reviewable project action"}
        )
        self.assertEqual(goal_response.status_code, 200)
        goal = goal_response.json()["data"]["goal"]
        run_response = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "title": "Ship the reviewed improvement",
                "steps": [{"client_key": "finish", "title": "Finish"}],
            },
        )
        self.assertEqual(run_response.status_code, 200)
        run = run_response.json()["data"]["run"]
        run_id = run["run_id"]
        self.assertEqual(
            self.client.post(f"/api/runs/{run_id}/start", headers=self.headers).status_code,
            200,
        )
        step = self.client.get(
            f"/api/runs/{run_id}", headers=self.headers
        ).json()["data"]["run"]["steps"][0]
        self.assertEqual(
            self.client.post(
                f"/api/runs/{run_id}/steps/{step['step_id']}/start",
                headers=self.headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                f"/api/runs/{run_id}/steps/{step['step_id']}/complete",
                headers=self.headers,
                json={},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.put(
                f"/api/runs/{run_id}/review",
                headers=self.headers,
                json={
                    "outcome": "met",
                    "rating": 4,
                    "notes": "Private reflection must not be copied into memory.",
                    "next_action": "Private next action must not be copied either.",
                },
            ).status_code,
            200,
        )

        suggestions_response = self.client.get(
            "/api/companion/memories/suggestions", headers=self.headers
        )
        self.assertEqual(suggestions_response.status_code, 200)
        suggestions = suggestions_response.json()["data"]["suggestions"]
        self.assertEqual(len(suggestions), 1)
        candidate = suggestions[0]
        memory_id = candidate["memory_id"]
        self.assertEqual(candidate["review_status"], "pending")
        self.assertFalse(candidate["use_in_context"])
        self.assertEqual(candidate["source_ref"], f"run:{run_id}:review")
        self.assertNotIn("Private reflection", candidate["content"])
        self.assertNotIn("Private next action", candidate["content"])
        self.assertEqual(candidate["evidence_refs"], [{"type": "task_run_review", "id": run_id}])

        before_confirmation = self.client.get(
            "/api/companion/context?sections=memories", headers=self.headers
        )
        self.assertEqual(before_confirmation.status_code, 200)
        self.assertEqual(
            before_confirmation.json()["data"]["context"]["sections"]["memories"], []
        )
        denied = self.client.patch(
            f"/api/companion/memories/{memory_id}/review",
            headers=self.other_headers,
            json={"decision": "confirmed"},
        )
        self.assertEqual(denied.status_code, 404)

        confirmed = self.client.patch(
            f"/api/companion/memories/{memory_id}/review",
            headers=self.headers,
            json={"decision": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["data"]["memory"]["review_status"], "confirmed")
        self.assertTrue(confirmed.json()["data"]["memory"]["use_in_context"])
        after_confirmation = self.client.get(
            "/api/companion/context?sections=memories", headers=self.headers
        )
        self.assertEqual(after_confirmation.status_code, 200)
        memory_items = after_confirmation.json()["data"]["context"]["sections"]["memories"]
        self.assertEqual(memory_items[0]["reference"]["id"], memory_id)
        self.assertEqual(
            memory_items[0]["selection"]["reason"],
            "Confirmed memory within the current privacy and freshness policy.",
        )

        self.assertEqual(
            self.client.delete(
                f"/api/companion/memories/{memory_id}", headers=self.headers
            ).status_code,
            200,
        )
        archived = self.client.get(
            "/api/companion/memories?status=archived", headers=self.headers
        ).json()["data"]["memories"]
        self.assertIn(memory_id, [item["memory_id"] for item in archived])
        self.assertEqual(
            self.client.delete(
                f"/api/companion/memories/{memory_id}/purge", headers=self.headers
            ).status_code,
            200,
        )
        remaining = self.client.get(
            "/api/companion/memories", headers=self.headers
        ).json()["data"]["memories"]
        self.assertNotIn(memory_id, [item["memory_id"] for item in remaining])


    def test_briefing_reports_every_visible_permission_as_a_real_context_source(self) -> None:
        permissions = {
            "profile": True,
            "goals": True,
            "runs": True,
            "growth": True,
            "memories": True,
            "knowledge": True,
            "rewards": True,
        }
        updated = self.client.put(
            "/api/companion/settings",
            headers=self.headers,
            json={"permissions": permissions},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["settings"]["permissions"], permissions)

        response = self.client.get("/api/companion/briefing", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        sources = response.json()["data"]["briefing"]["context"]["sources"]
        self.assertEqual({source["section"] for source in sources}, set(permissions))
        self.assertTrue(all(source["permission"] for source in sources))
        self.assertFalse(any(source["reason"] == "Not enabled in companion settings." for source in sources))



    def _seed_profile_hypothesis(self, owner_id: str, *, key: str = "keeps-next-actions") -> str:
        connection = self.client.app.state.database.get_connection()
        try:
            connection.execute(
                """INSERT INTO profile_signals
                   (signal_id, owner_id, kind, summary, source_type, source_ref, attributes,
                    weight, observed_at, sensitivity, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "signal-1", owner_id, "task", "已记录 3 次任务复盘，其中 2 次留下后续行动。",
                    "workspace_history_summary", "task_reviews:v1", "{}", 0.8,
                    "2026-07-19T10:00:00+00:00", "private", "active",
                    "2026-07-19T10:00:00+00:00", "2026-07-19T10:00:00+00:00",
                ),
            )
            connection.execute(
                """INSERT INTO profile_hypotheses
                   (hypothesis_id, owner_id, domain, profile_key, value, summary, rationale,
                    confidence, evidence_refs, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (
                    "hypothesis-1", owner_id, "working_style", key,
                    "倾向于在复盘后留下下一步行动。", "复盘后倾向于留下下一步行动",
                    "已授权的任务汇总记录显示，多次复盘保留了后续行动。", 0.8,
                    '[{"type":"profile_signal","id":"signal-1"}]',
                    "2026-07-19T10:00:00+00:00", "2026-07-19T10:00:00+00:00",
                ),
            )
            connection.commit()
            return "hypothesis-1"
        finally:
            connection.close()

    def test_profile_workspace_uses_canonical_layers_and_hides_raw_text(self) -> None:
        self._enable_profile_analysis(self.headers)
        owner_id = self._owner_id("owner")
        self._seed_profile_hypothesis(owner_id)

        profile = self.client.get("/api/companion/profile", headers=self.headers)
        self.assertEqual(profile.status_code, 200)
        payload = profile.json()["data"]["profile"]
        self.assertEqual(payload["summary"]["reviewing"], 1)
        self.assertEqual(payload["signals"][0]["label"], "任务复盘")
        self.assertEqual(payload["hypotheses"][0]["hypothesis_id"], "hypothesis-1")
        self.assertNotIn("signal-1", str(payload))
        self.assertNotIn("observations", payload)

    def test_confirmed_hypothesis_becomes_the_only_profile_context_projection(self) -> None:
        self._enable_profile_analysis(self.headers)
        owner_id = self._owner_id("owner")
        hypothesis_id = self._seed_profile_hypothesis(owner_id)

        reviewed = self.client.patch(
            f"/api/companion/profile/hypotheses/{hypothesis_id}/review",
            headers=self.headers,
            json={"decision": "confirmed"},
        )
        self.assertEqual(reviewed.status_code, 200)
        profile = reviewed.json()["data"]["profile"]
        self.assertEqual(profile["summary"]["established"], 1)
        self.assertEqual(profile["summary"]["reviewing"], 0)

        context = self.client.get(
            "/api/companion/context?sections=profile", headers=self.headers
        )
        self.assertEqual(context.status_code, 200)
        items = context.json()["data"]["context"]["sections"]["profile"]
        facets = [item for item in items if item["kind"] == "profile_facet"]
        self.assertEqual(len(facets), 1)
        self.assertEqual(facets[0]["data"]["value"], "倾向于在复盘后留下下一步行动。")
        self.assertEqual(facets[0]["provenance"]["source"], "layered_profile")

    def test_rejected_hypothesis_suppresses_the_same_key_and_legacy_routes_are_gone(self) -> None:
        self._enable_profile_analysis(self.headers)
        owner_id = self._owner_id("owner")
        hypothesis_id = self._seed_profile_hypothesis(owner_id, key="review-style")
        rejected = self.client.patch(
            f"/api/companion/profile/hypotheses/{hypothesis_id}/review",
            headers=self.headers,
            json={"decision": "rejected", "reason": "不符合我的实际情况"},
        )
        self.assertEqual(rejected.status_code, 200)
        connection = self.client.app.state.database.get_connection()
        try:
            suppression = connection.execute(
                "SELECT status FROM profile_suppressions WHERE owner_id = ? AND profile_key = ?",
                (owner_id, "review-style"),
            ).fetchone()
            self.assertEqual(suppression["status"], "active")
        finally:
            connection.close()
        self.assertEqual(
            self.client.get("/api/companion/profile/suggestions", headers=self.headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/companion/profile/observations", headers=self.headers).status_code,
            404,
        )



if __name__ == "__main__":
    unittest.main()

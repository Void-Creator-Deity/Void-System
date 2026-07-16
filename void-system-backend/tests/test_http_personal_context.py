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

    def test_profile_observations_are_owner_scoped(self) -> None:
        created = self.client.post(
            "/api/companion/profile/observations",
            headers=self.headers,
            json={
                "kind": "favorite",
                "summary": "Saved several practical interface design references.",
                "source_type": "favorites_import",
                "source_ref": "collection:design",
                "attributes": {"platform": "example", "topic": "interface-design"},
                "weight": 0.8,
            },
        )
        self.assertEqual(created.status_code, 200)
        observation = created.json()["data"]["observation"]
        self.assertEqual(observation["attributes"]["topic"], "interface-design")
        self.assertTrue(observation["observed_at"])

        owned = self.client.get(
            "/api/companion/profile/observations", headers=self.headers
        ).json()["data"]["observations"]
        other = self.client.get(
            "/api/companion/profile/observations", headers=self.other_headers
        ).json()["data"]["observations"]
        self.assertEqual(len(owned), 1)
        self.assertEqual(other, [])

    def test_profile_claim_review_preserves_raw_value_and_applies_reversible_override(self) -> None:
        self._enable_profile_analysis(self.headers)
        created = self.client.post(
            "/api/companion/profile/claims",
            headers=self.headers,
            json={
                "domain": "communication",
                "profile_key": "沟通偏好",
                "value": "Provide detailed background first",
                "summary": "Preferred answer structure",
                "rationale": "Inferred from prior feedback.",
                "confidence": 0.6,
                "evidence_refs": [{"type": "observation", "id": "feedback-1"}],
            },
        )
        self.assertEqual(created.status_code, 200)
        claim = created.json()["data"]["claim"]
        self.assertEqual(claim["profile_key"], "沟通偏好")

        pending_profile = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        self.assertFalse(pending_profile["effective_claims"][0]["context_eligible"])
        other_profile = self.client.get(
            "/api/companion/profile", headers=self.other_headers
        ).json()["data"]["profile"]
        self.assertEqual(other_profile["raw_claims"], [])

        corrected = self.client.patch(
            f"/api/companion/profile/claims/{claim['claim_id']}/review",
            headers=self.headers,
            json={
                "decision": "corrected",
                "value": "Lead with the conclusion, then explain",
                "reason": "User correction",
            },
        )
        self.assertEqual(corrected.status_code, 200)
        corrected_profile = corrected.json()["data"]["profile"]
        self.assertEqual(
            corrected_profile["raw_claims"][0]["value"],
            "Provide detailed background first",
        )
        self.assertEqual(
            corrected_profile["effective_claims"][0]["value"],
            "Lead with the conclusion, then explain",
        )
        self.assertEqual(
            corrected_profile["effective_claims"][0]["effective_source"],
            "user_override",
        )
        feedback = self.client.get(
            "/api/companion/profile/observations", headers=self.headers
        ).json()["data"]["observations"]
        feedback_records = [
            item for item in feedback if item["source_type"] == "profile_claim_review"
        ]
        self.assertEqual(len(feedback_records), 1)
        feedback_record = feedback_records[0]
        self.assertEqual(feedback_record["attributes"]["decision"], "corrected")
        self.assertTrue(feedback_record["attributes"]["has_correction"])
        self.assertNotIn("Lead with the conclusion", feedback_record["summary"])
        self.assertNotIn("Lead with the conclusion", str(feedback_record["attributes"]))

        context = self.client.get(
            "/api/companion/context?sections=profile", headers=self.headers
        ).json()["data"]["context"]
        claims = [
            item for item in context["sections"]["profile"]
            if item["kind"] == "profile_claim"
        ]
        self.assertEqual(claims[0]["data"]["value"], "Lead with the conclusion, then explain")
        self.assertEqual(claims[0]["provenance"]["source"], "profile_cognition")

        reset = self.client.patch(
            f"/api/companion/profile/claims/{claim['claim_id']}/review",
            headers=self.headers,
            json={"decision": "pending"},
        )
        reset_profile = reset.json()["data"]["profile"]
        self.assertEqual(
            reset_profile["effective_claims"][0]["value"],
            "Provide detailed background first",
        )
        self.assertFalse(reset_profile["effective_claims"][0]["context_eligible"])
        reset_feedback = self.client.get(
            "/api/companion/profile/observations", headers=self.headers
        ).json()["data"]["observations"]
        reset_records = [
            item for item in reset_feedback if item["source_type"] == "profile_claim_review"
        ]
        self.assertEqual(len(reset_records), 1)
        self.assertEqual(reset_records[0]["observation_id"], feedback_record["observation_id"])
        self.assertEqual(reset_records[0]["attributes"]["decision"], "pending")

        rejected = self.client.patch(
            f"/api/companion/profile/claims/{claim['claim_id']}/review",
            headers=self.headers,
            json={"decision": "rejected", "reason": "Not representative"},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["data"]["profile"]["effective_claims"], [])

    def test_memory_profile_consent_is_explicit_and_reviewable(self) -> None:
        ordinary_memory = self.client.post(
            "/api/companion/memories",
            headers=self.headers,
            json={
                "memory_type": "preference",
                "title": "Ordinary note",
                "content": "Keep this as a memory, not a profile conclusion.",
            },
        ).json()["data"]["memory"]
        self.assertFalse(ordinary_memory["metadata"].get("contribute_to_profile", False))
        empty_profile = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        self.assertEqual(empty_profile["raw_claims"], [])

        memory = self.client.post(
            "/api/companion/memories",
            headers=self.headers,
            json={
                "memory_type": "inference",
                "title": "Prefers reviewable steps",
                "content": "Break work into checkpoints with evidence.",
                "source_type": "run_evaluation",
                "confidence": 0.82,
                "contribute_to_profile": True,
            },
        ).json()["data"]["memory"]
        self.assertTrue(memory["metadata"]["contribute_to_profile"])
        profile = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        self.assertEqual(profile["raw_claims"][0]["review_status"], "pending")
        self.assertFalse(profile["effective_claims"][0]["context_eligible"])

        self.client.patch(
            f"/api/companion/memories/{memory['memory_id']}",
            headers=self.headers,
            json={"contribute_to_profile": False},
        )
        profile_after_opt_out = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        self.assertEqual(profile_after_opt_out["raw_claims"], [])

        disabled = self.client.put(
            "/api/companion/settings",
            headers=self.headers,
            json={"permissions": {"profile": False}},
        )
        self.assertEqual(disabled.status_code, 200)
        context = self.client.get(
            "/api/companion/context?sections=profile", headers=self.headers
        ).json()["data"]["context"]
        self.assertNotIn("profile", context["included_sections"])

        deleted = self.client.delete(
            f"/api/companion/memories/{memory['memory_id']}", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 200)
        profile_after_delete = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        self.assertEqual(profile_after_delete["raw_claims"], [])


    def test_task_history_suggestions_are_reviewable_and_owner_scoped(self) -> None:
        empty = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["suggestions"], [])
        self._enable_profile_analysis(self.headers)

        for index in range(4):
            goal = self.client.post(
                "/api/goals",
                headers=self.headers,
                json={"title": f"Finish structured action {index}"},
            ).json()["data"]["goal"]
            run = self.client.post(
                f"/api/goals/{goal['goal_id']}/runs",
                headers=self.headers,
                json={
                    "title": f"Structured action {index}",
                    "mode": "assisted",
                    "steps": [
                        {"client_key": "prepare", "title": "Prepare"},
                        {
                            "client_key": "finish",
                            "title": "Finish",
                            "depends_on": ["prepare"],
                        },
                    ],
                },
            ).json()["data"]["run"]
            self.assertEqual(
                self.client.post(
                    f"/api/runs/{run['run_id']}/start", headers=self.headers
                ).status_code,
                200,
            )
            for step in self.client.get(
                f"/api/runs/{run['run_id']}", headers=self.headers
            ).json()["data"]["run"]["steps"]:
                self.assertEqual(
                    self.client.post(
                        f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start",
                        headers=self.headers,
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.post(
                        f"/api/runs/{run['run_id']}/steps/{step['step_id']}/complete",
                        headers=self.headers,
                        json={},
                    ).status_code,
                    200,
                )
            self.assertEqual(
                self.client.put(
                    f"/api/runs/{run['run_id']}/review",
                    headers=self.headers,
                    json={"rating": 4, "next_action": "Choose the next small action"},
                ).status_code,
                200,
            )

        suggestions_response = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        )
        self.assertEqual(suggestions_response.status_code, 200)
        suggestions = suggestions_response.json()["data"]["suggestions"]
        self.assertTrue(suggestions)
        self.assertTrue(all(item["action"] == "review_required" for item in suggestions))
        self.assertTrue(all(item["source"] == "your_action_history" for item in suggestions))
        self.assertTrue(all("notes" not in str(item["evidence_refs"]) for item in suggestions))
        self.assertTrue(all(item["first_observed_at"] for item in suggestions))
        self.assertTrue(all(item["last_observed_at"] for item in suggestions))
        self.assertTrue(all(
            item["evidence_refs"][0]["data"]["observed_from"] == item["first_observed_at"]
            for item in suggestions
        ))
        self.assertTrue(all(
            item["evidence_refs"][0]["data"]["observed_to"] == item["last_observed_at"]
            for item in suggestions
        ))
        follow_up = next(
            item for item in suggestions
            if item["suggestion_id"] == "task_behavior:follow_up_after_review"
        )

        other = self.client.get(
            "/api/companion/profile/suggestions", headers=self.other_headers
        )
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["data"]["suggestions"], [])

        reviewed = self.client.post(
            f"/api/companion/profile/suggestions/{follow_up['suggestion_id']}/review",
            headers=self.headers,
            json={"decision": "confirmed"},
        )
        self.assertEqual(reviewed.status_code, 200)
        claim = reviewed.json()["data"]["claim"]
        self.assertEqual(claim["review_status"], "confirmed")
        self.assertEqual(claim["profile_key"], "behavior:follow_up_after_review")
        self.assertEqual(claim["first_observed_at"], follow_up["first_observed_at"])
        self.assertEqual(claim["last_observed_at"], follow_up["last_observed_at"])
        self.assertEqual(
            claim["value"],
            {
                "kind": "task_behavior",
                "pattern": "follow_up_after_review",
                "label": "You often turn a completed action into a concrete next step.",
            },
        )

        after_review = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        ).json()["data"]["suggestions"]
        self.assertNotIn(follow_up["suggestion_id"], [item["suggestion_id"] for item in after_review])

        profile = self.client.get("/api/companion/profile", headers=self.headers).json()["data"]["profile"]
        saved = next(
            item for item in profile["effective_claims"]
            if item["profile_key"] == "behavior:follow_up_after_review"
        )
        self.assertTrue(saved["context_eligible"])

    def test_knowledge_use_suggestions_require_profile_permission_and_stay_owner_scoped(self) -> None:
        owner_id = self._owner_id("owner")
        repository = SQLiteKnowledgeLifecycleRepository(
            self.client.app.state.database.get_connection
        )
        for _ in range(4):
            repository.record_knowledge_use(
                owner_id=owner_id,
                mode="hybrid",
                candidate_count=3,
                ranked_count=2,
                source_count=1,
                citation_count=1,
                answerable=True,
            )
        repository.record_knowledge_use(
            owner_id=owner_id,
            mode="hybrid",
            candidate_count=2,
            ranked_count=0,
            source_count=0,
            citation_count=0,
            answerable=False,
        )

        disabled = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.json()["data"]["suggestions"], [])

        self._enable_profile_analysis(self.headers)
        suggestions = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        ).json()["data"]["suggestions"]
        suggestion = next(
            item
            for item in suggestions
            if item["suggestion_id"] == "knowledge_behavior:evidence_backed_reference"
        )
        self.assertEqual(suggestion["source"], "your_knowledge_use_history")
        evidence = suggestion["evidence_refs"][0]["data"]
        self.assertEqual(evidence["knowledge_use_count"], 5)
        self.assertEqual(evidence["reliable_use_count"], 4)
        self.assertNotIn("question", str(suggestion).lower())
        self.assertNotIn("source_id", str(suggestion).lower())

        other = self.client.get(
            "/api/companion/profile/suggestions", headers=self.other_headers
        )
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["data"]["suggestions"], [])

    def test_corrected_profile_suggestion_requires_a_value(self) -> None:
        self._enable_profile_analysis(self.headers)
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Review action"}
        ).json()["data"]["goal"]
        for index in range(3):
            run = self.client.post(
                f"/api/goals/{goal['goal_id']}/runs",
                headers=self.headers,
                json={
                    "title": f"Reviewable action {index}",
                    "steps": [{"client_key": "finish", "title": "Finish"}],
                },
            ).json()["data"]["run"]
            self.client.post(f"/api/runs/{run['run_id']}/start", headers=self.headers)
            step = self.client.get(
                f"/api/runs/{run['run_id']}", headers=self.headers
            ).json()["data"]["run"]["steps"][0]
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start", headers=self.headers
            )
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/complete",
                headers=self.headers,
                json={},
            )
            self.client.put(
                f"/api/runs/{run['run_id']}/review",
                headers=self.headers,
                json={"next_action": "Write the next step"},
            )

        response = self.client.post(
            "/api/companion/profile/suggestions/task_behavior:follow_up_after_review/review",
            headers=self.headers,
            json={"decision": "corrected", "value": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "PROFILE_CORRECTION_REQUIRED")
        profile = self.client.get("/api/companion/profile", headers=self.headers).json()["data"]["profile"]
        self.assertEqual(profile["raw_claims"], [])

    def test_rejected_profile_suggestion_is_not_shown_again(self) -> None:
        self._enable_profile_analysis(self.headers)
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Action with a next step"}
        ).json()["data"]["goal"]
        for index in range(3):
            run = self.client.post(
                f"/api/goals/{goal['goal_id']}/runs",
                headers=self.headers,
                json={
                    "title": f"Reviewable action {index}",
                    "steps": [{"client_key": "finish", "title": "Finish"}],
                },
            ).json()["data"]["run"]
            self.client.post(f"/api/runs/{run['run_id']}/start", headers=self.headers)
            step = self.client.get(
                f"/api/runs/{run['run_id']}", headers=self.headers
            ).json()["data"]["run"]["steps"][0]
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start", headers=self.headers
            )
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/complete",
                headers=self.headers,
                json={},
            )
            self.client.put(
                f"/api/runs/{run['run_id']}/review",
                headers=self.headers,
                json={"next_action": "Write the next step"},
            )
        suggestion_id = "task_behavior:follow_up_after_review"
        rejected = self.client.post(
            f"/api/companion/profile/suggestions/{suggestion_id}/review",
            headers=self.headers,
            json={"decision": "rejected", "reason": "Not useful"},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["data"]["claim"]["review_status"], "rejected")
        remaining = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        ).json()["data"]["suggestions"]
        self.assertNotIn(suggestion_id, [item["suggestion_id"] for item in remaining])

    def test_resetting_a_rejected_suggestion_keeps_a_single_pending_claim(self) -> None:
        self._enable_profile_analysis(self.headers)
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Action with a next step"}
        ).json()["data"]["goal"]
        for index in range(3):
            run = self.client.post(
                f"/api/goals/{goal['goal_id']}/runs",
                headers=self.headers,
                json={
                    "title": f"Reviewable action {index}",
                    "steps": [{"client_key": "finish", "title": "Finish"}],
                },
            ).json()["data"]["run"]
            self.client.post(f"/api/runs/{run['run_id']}/start", headers=self.headers)
            step = self.client.get(
                f"/api/runs/{run['run_id']}", headers=self.headers
            ).json()["data"]["run"]["steps"][0]
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/start", headers=self.headers
            )
            self.client.post(
                f"/api/runs/{run['run_id']}/steps/{step['step_id']}/complete",
                headers=self.headers,
                json={},
            )
            self.client.put(
                f"/api/runs/{run['run_id']}/review",
                headers=self.headers,
                json={"next_action": "Write the next step"},
            )

        suggestion_id = "task_behavior:follow_up_after_review"
        rejected = self.client.post(
            f"/api/companion/profile/suggestions/{suggestion_id}/review",
            headers=self.headers,
            json={"decision": "rejected"},
        )
        self.assertEqual(rejected.status_code, 200)
        claim_id = rejected.json()["data"]["claim"]["claim_id"]

        reset = self.client.patch(
            f"/api/companion/profile/claims/{claim_id}/review",
            headers=self.headers,
            json={"decision": "pending"},
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["data"]["claim"]["review_status"], "pending")

        suggestions = self.client.get(
            "/api/companion/profile/suggestions", headers=self.headers
        ).json()["data"]["suggestions"]
        self.assertNotIn(suggestion_id, [item["suggestion_id"] for item in suggestions])

        profile = self.client.get(
            "/api/companion/profile", headers=self.headers
        ).json()["data"]["profile"]
        matching = [
            item
            for item in profile["raw_claims"]
            if item["domain"] == "working_style"
            and item["profile_key"] == "behavior:follow_up_after_review"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["review_status"], "pending")


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


if __name__ == "__main__":
    unittest.main()

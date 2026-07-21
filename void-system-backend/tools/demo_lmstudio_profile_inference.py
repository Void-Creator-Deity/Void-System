"""Run a disposable LM Studio profile-inference integration check.

This script never reads or changes the application .env, the production SQLite
store, or real user accounts. It only runs when explicitly enabled.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from adapters.sqlite.identity_repository import SQLiteIdentityRepository
from adapters.sqlite.personal_context_repository import SQLitePersonalContextRepository
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.personal_context.context import ContextAssembler
from modules.personal_context.inference import ProfileInference
from modules.personal_context.profile import ProfileCognition
from modules.personal_context.service import PersonalContext


LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "google/gemma-4-12b-qat"
_PLANNING_DOMAINS = {"working_style", "current_phase", "interests"}


class _EmptyTasks:
    def list_goals(self, owner_id: str, *, status: str):
        return []

    def list_runs(self, owner_id: str):
        return []


class _EmptyGrowth:
    def list_capabilities(self, owner_id: str):
        return []


class _EmptyKnowledge:
    pass


def _context(database: Database) -> PersonalContext:
    settings = RuntimeSettings(
        LLM_PROVIDER="lmstudio",
        CHAT_MODEL=LM_STUDIO_MODEL,
        OPENAI_BASE_URL=LM_STUDIO_BASE_URL,
        DATABASE_URL="sqlite:///temporary-lmstudio-profile-demo.db",
    )
    repository = SQLitePersonalContextRepository(database.get_connection)
    return PersonalContext(
        repository,
        ContextAssembler(_EmptyTasks(), _EmptyGrowth(), _EmptyKnowledge()),
        ProfileCognition(repository),
        profile_inference=ProfileInference(settings),
    )


def run_demo() -> None:
    if os.environ.get("RUN_LMSTUDIO_INTEGRATION") != "1":
        raise SystemExit(
            "Set RUN_LMSTUDIO_INTEGRATION=1 to run the disposable local LM Studio check."
        )

    with tempfile.TemporaryDirectory(prefix="void-system-lmstudio-profile-") as directory:
        database = Database(str(Path(directory) / "profile-demo.db"))
        owner_id = SQLiteIdentityRepository(database.get_connection).add_user(
            "lmstudio-profile-demo", "lmstudio-profile-demo@example.invalid", "not-used"
        )
        if owner_id is None:
            raise SystemExit("Unable to create the synthetic LM Studio demo account.")
        companion = _context(database)
        companion.update_settings(owner_id, {"permissions": {"profile": True}})

        for index, summary in enumerate(
            (
                "The demo user asks for plans with a checklist and one clear next step.",
                "The demo user records a short review after each completed milestone.",
                "The demo user prefers a weekly focus plan instead of a large unprioritized backlog.",
            ),
            start=1,
        ):
            companion.create_signal(
                owner_id,
                {
                    "kind": "task" if index < 3 else "feedback",
                    "summary": summary,
                    "source_type": "lmstudio_integration_demo",
                    "source_ref": f"synthetic-demo:{index}",
                    "attributes": {"synthetic": True},
                    "weight": 1.0,
                    "sensitivity": "private",
                    "status": "active",
                },
            )

        result = companion.infer_profile_hypotheses(
            owner_id, max_signals=12, max_hypotheses=3
        )
        hypotheses = result["hypotheses"]
        if not hypotheses:
            raise SystemExit("LM Studio returned no profile hypotheses for the synthetic demo data.")
        if any(hypothesis["status"] != "pending" for hypothesis in hypotheses):
            raise SystemExit("Profile hypotheses were not stored as pending review items.")

        pending_view = companion.get_profile_view(owner_id)
        if pending_view["facets"]:
            raise SystemExit("Pending profile hypotheses leaked into the confirmed profile.")

        reviewable = next(
            (hypothesis for hypothesis in hypotheses if hypothesis["domain"] in _PLANNING_DOMAINS),
            None,
        )
        if reviewable is None:
            raise SystemExit(
                "LM Studio hypotheses did not include a planning-safe profile domain for this demo."
            )
        companion.review_profile_hypothesis(
            owner_id,
            reviewable["hypothesis_id"],
            {"decision": "confirmed"},
        )

        snapshot = companion.build_ai_context(
            owner_id,
            {"username": "Synthetic demo user", "role": "user"},
            purpose="planning_assist",
        )
        rendered = companion.render_ai_context(snapshot)
        if str(reviewable["value"]) not in rendered:
            raise SystemExit("Confirmed profile understanding was missing from planning context.")
        if any(
            item.get("data", {}).get("domain") not in _PLANNING_DOMAINS
            for item in snapshot["sections"].get("profile", [])
            if item.get("kind") == "profile_facet"
        ):
            raise SystemExit("Planning context included a disallowed profile domain.")

        print(
            "LM Studio profile inference passed: "
            f"{len(hypotheses)} pending hypothesis/hypotheses, then one confirmed understanding "
            "was included in the explainable planning context."
        )


if __name__ == "__main__":
    run_demo()
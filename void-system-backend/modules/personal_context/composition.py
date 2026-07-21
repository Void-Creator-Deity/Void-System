"""Composition helpers for Personal Context outside FastAPI request dependencies."""
from __future__ import annotations

from database import Database
from core.runtime_settings import RuntimeSettings
from adapters.sqlite.personal_context_repository import SQLitePersonalContextRepository
from modules.growth.service import get_growth_profile
from modules.knowledge.service import create_user_knowledge_workspace
from modules.personal_context.context import ContextAssembler
from modules.personal_context.evidence import ProfileEvidenceCollector
from modules.personal_context.inference import ProfileInference
from modules.personal_context.layered_profile import LayeredProfileWorkspace
from modules.personal_context.profile import ProfileCognition
from modules.personal_context.service import PersonalContext
from modules.tasks.service import get_task_execution


def compose_personal_context(database: Database, settings: RuntimeSettings) -> PersonalContext:
    """Compose permissioned Personal Context for HTTP and durable background workers.

    Inputs:
        database: Application-owned SQLite facade.
        settings: Current runtime model configuration used for optional profile inference.
    Outputs:
        A PersonalContext module with canonical task, growth, knowledge, memory, and profile sources.
    Called by:
        FastAPI dependency construction and PlanGenerationWorker job execution.
    Side effects:
        Creates lightweight adapters only; knowledge maintenance remains lazy until a caller needs it.
    Failure:
        Adapter construction errors propagate to the application composition boundary.
    Invariants:
        Request and worker paths use identical consent, context-policy, and inference behavior.
    """
    task_execution = get_task_execution(database)
    growth_profile = get_growth_profile(database)
    knowledge_workspace = create_user_knowledge_workspace(database, settings)
    repository = SQLitePersonalContextRepository(database.get_connection)
    profile_cognition = ProfileCognition(repository)
    return PersonalContext(
        repository,
        ContextAssembler(task_execution, growth_profile, knowledge_workspace),
        profile_cognition,
        profile_inference=ProfileInference(settings),
        profile_evidence_collector=ProfileEvidenceCollector(task_execution, profile_cognition),
        layered_profile=LayeredProfileWorkspace(),
    )

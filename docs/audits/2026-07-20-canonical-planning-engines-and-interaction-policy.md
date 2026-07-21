# Canonical Planning Engines and Interaction Policy Audit

- Status: Implemented and verified
- Date: 2026-07-20
- Scope: Remove the active legacy planning adapter and make companion interaction settings effective for durable plan generation without granting them control over planning semantics.

## Observed State

Durable Plan Generation and Plan Drafts are the canonical planning path, but their active composition point imports `LegacyAdvisorPlanningEngine` and `LegacyTaskEvaluationEngine` from `adapters/legacy/planning_adapters.py`. The adapter is active runtime code rather than a one-time migration or archived record.

Companion settings already persist `tone`, `initiative`, and a bounded persona profile. Persona chat reads those settings, but plan generation only reads user context and advisor preferences. A user changing the companion interaction controls therefore sees no documented or testable effect on plan wording.

## Root Cause

The planning contract has no interaction-policy field, and runtime composition still uses a transitional adapter filename and type names. The one-pass planner is technically canonical, but its boundary does not describe that fact or receive the allowed collaboration settings.

## Canonical Repair

1. Move the active planning and task-evaluation adapter into `adapters/ai/` and remove the legacy module after import scans prove it is unused.
2. Keep `PlanRequest` as the portable planner boundary and add an immutable, typed interaction policy containing only supported `tone` and `initiative` choices.
3. Resolve that policy server-side from the owner’s persisted companion settings when the background job executes. Do not store user-authored persona text in the plan-generation job snapshot.
4. Render only a bounded presentation instruction for the model: tone controls wording; initiative controls whether one optional immediate next action may be included. It cannot alter JSON schema, execution mode, authorization, context permissions, task state, rewards, or completion rules.
5. Preserve the single model-call structured plan generation and its strict local normalization contract.

## Affected Layers

- Core: `PlanRequest` and planning interaction-policy value contract.
- Module: durable plan-generation context assembly and server-side settings resolution.
- Adapter: canonical AI planning/evaluation adapter and prompt parameter propagation.
- AI service: structured planner prompt receives a lower-priority collaboration instruction.
- Tests: policy resolution, anti-injection behavior, adapter runtime settings, and planner propagation.
- Data/API: no schema or HTTP-contract change. Existing persisted jobs remain valid because policy is resolved at execution time.

## Legacy Removal Conditions

Delete `adapters/legacy/planning_adapters.py` only after every runtime import and test has moved to `adapters/ai/planning_engines.py`, the full backend suite passes, and a repository scan finds no old planning adapter name or module import outside historical docs.

## Verification

Verified on 2026-07-20:

- Focused planning policy tests: 8 passing, including settings normalization, adapter runtime scoping, persona-injection exclusion, and durable generation propagation.
- Backend suite: 208 passing using void-system-backend/.venv313.
- Frontend production build: passing.
- Frontend test suite: 28 passing.
- Legacy planning adapter scan: no references to legacy.planning_adapters, LegacyAdvisorPlanningEngine, or LegacyTaskEvaluationEngine.
- git diff --check: passing.

The expected failure-path test logs for unavailable database, vision, and vector dependencies appeared during the backend suite; their assertions passed and the suite ended successfully.

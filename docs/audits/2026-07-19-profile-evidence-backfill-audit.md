# Profile Evidence Backfill Audit

- Status: Implemented and verified; live LM Studio smoke test blocked by a stopped local service
- Date: 2026-07-19
- Scope: Personal Context profile inference evidence collection

## Observed State

The profile inference endpoint reads only active records from `profile_observations`. Existing task history, plan publication, task-step progress, and completed reviews are not converted into observations unless a new run review is recorded through the current event hook. In the production workspace, the administrator account has substantial task history but only one active observation, while inference correctly requires three safe observations before it invokes the model.

## Root Cause

The profile inference module and the historical Workspace data model are disconnected. The behavior-insight reader can aggregate task history for deterministic UI suggestions, but no canonical module turns those conservative aggregates into idempotent, reviewable profile observations before LLM inference. The missing bridge makes the user-facing "organize from existing records" action falsely appear supported.

## Canonical Repair

Introduce a `ProfileEvidenceCollector` in `modules/personal_context`. It reads the existing task behavior source and upserts only conservative aggregate observations with deterministic source references. The collector runs only after the owner has enabled the `profile` permission and immediately before profile inference reads evidence. It never collects arbitrary chat content, raw review notes, artifact contents, uploaded document bodies, sensitive data, or external-platform data.

The initial evidence categories are:

1. Execution history, once at least three recorded runs exist.
2. Structured work history, once at least six recorded steps exist.
3. Review history, once at least one task review exists.
4. Recovery/refinement history only when the relevant aggregate signals meet their own thresholds.

Repeated collection updates the same observation rather than adding duplicates. LLM output remains a pending claim and is excluded from effective profile context until the user confirms or corrects it.

## Affected Layers

- Domain module: Personal Context evidence collection and inference orchestration
- Adapter contract: existing task behavior aggregate reader
- SQLite persistence: existing idempotent `profile_observations` upsert path; no schema migration
- HTTP: existing inference route gains real historical evidence coverage without a new route
- Frontend: inference result reports the evidence count that was actually considered
- Tests: collection thresholds, idempotency, consent boundary, pending-review behavior, HTTP integration

## Legacy / Migration Decision

No compatibility route, duplicate table, or historical runtime adapter is introduced. Existing profile observations remain valid. Historical task data is projected into the canonical observation table at inference time through deterministic source references, so no one-time bulk migration or legacy reader must remain active.

## Verification

- Backend compile passed for the Personal Context module, task aggregate repository, and profile evidence tests.
- Backend regression passed: 48 tests across profile evidence, profile inference, Personal Context policy and HTTP, AI HTTP, behavior insights, and task execution.
- Frontend production build passed.
- Production-record evidence check: the consented administrator history refreshed four deterministic observations for goals, runs, steps, and reviews. Existing observations remain separate and no profile claim was auto-confirmed.
- Static diff validation passed; only existing CRLF normalization warnings were emitted.
- Live LM Studio inference remains unverified because http://127.0.0.1:1234/v1/models was unreachable on 2026-07-19. The disposable smoke test must be rerun only after the user-controlled local service starts.

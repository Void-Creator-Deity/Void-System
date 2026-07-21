# Companion Interaction and Assisted Completion Audit

- Status: Implemented; automated regression verification complete
- Product decision recorded: 2026-07-20 — manual work is directly completed by the user; system-assisted work is submitted to the companion for an AI review. Companion chat remains available in both modes.
- Date: 2026-07-20
- Scope: Make companion interaction preferences effective and consolidate task completion into manual and system-assisted paths.

## Observed State

The Companion screen exposes tone (`calm`, `warm`, `direct`) and initiative (`quiet`, `balanced`, `proactive`) controls. Their values are persisted in `companion_settings`, but the persona-chat system prompt is hard-coded as calm, precise, and practical. The controls therefore do not consistently affect model behavior.

The Task Workspace exposes three execution modes: `manual`, `assisted`, and `agent`. Plan publication currently serializes both `manual` and `assisted` steps as `manual`; only `agent` receives a distinct step kind. No application-owned worker performs generic agent steps. The product therefore exposes two modes whose behavior is currently indistinguishable and one mode that promises automatic execution without a complete execution path.

## Root Cause

Preference persistence and AI prompt composition are separate paths without a shared interaction-policy contract. Task run mode is stored as a label before the downstream completion semantics have been implemented.

## Canonical Repair

The user-facing task contract has two modes:

1. `manual`: an ordinary to-do. The user records evidence and marks the step complete.
2. `assisted`: the user records evidence, then requests a system-companion review. The review must return a visible pass or revision result, retain the submitted evidence, and never silently complete a step after a model failure.

The system companion remains available for questions in both modes. Automatic execution is not shown as a user mode until a real tool-authorized worker, durable job model, progress stream, approval boundary, and retry/recovery behavior are delivered together.

Companion interaction settings become one structured policy delivered to every first-party AI call. A separately stored persona profile may express a preferred name, role, and concise collaboration brief. It is user-controlled and auditable, while core system instructions, access permissions, and safety boundaries remain outside user-editable text.

## Affected Layers

- Domain contracts: canonical task modes, assisted-review outcome, companion interaction policy
- Module: Task Execution and Personal Context
- Persistence: settings migration and durable review records if asynchronous review is required
- HTTP: settings contract and assisted-completion endpoint
- Frontend: task mode selector, completion dialog, companion settings
- Verification: unit, HTTP, frontend contract, production build, and live model smoke test after user starts LM Studio

## Legacy and Data Strategy

Existing `agent` run records are historical records only. New clients must not create them. Existing history remains readable and is rendered as a historical system-assisted record after migration; old claim/lease endpoints are deleted only after no first-party route or scheduled worker consumes them.

No fallback may treat an assisted submission as manually completed. If the configured AI service is unavailable, the submitted evidence remains available for retry and the step stays open.

## Acceptance Criteria

1. Changing tone or initiative changes a documented, testable portion of the system instruction for persona chat and planning assistance.
2. Persona profile edits are persisted, bounded, visible to the user, and cannot grant data access or override core instructions.
3. New plans and manual runs expose only manual and system-assisted modes.
4. Manual completion does not call an AI evaluator.
5. Assisted completion keeps evidence, yields a review result, and completes the step only on an explicit successful review.
6. The same semantics survive refresh, retries, API failures, and application restarts.

## Verification Record

On 2026-07-20, the shared companion interaction policy was verified through the canonical planning adapter and durable Plan Generation path. The 208-test backend suite and 28-test frontend suite passed, along with the frontend production build. A live LM Studio smoke test remains a deployment-time check because it depends on the user-run local model service rather than an application-owned test fixture.

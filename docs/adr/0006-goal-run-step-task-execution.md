# ADR-0006: Goal, Run, and Step Task Execution

- Status: Accepted, backend implemented
- Date: 2026-07-15

## Context

The original task system models standalone tasks, automatic tasks, and task chains as different product concepts. Execution state is spread across `tasks`, `task_chains`, prerequisite JSON, planning code, HTTP routes, and reward logic. The model can represent a linear checklist, but it has no durable Run lifecycle, append-only history, approval state, retry attempt, artifact record, or reliable Step dependency graph.

That split forced clients to understand historical implementation categories instead of a single execution model. It also made refresh recovery, review, and migration behavior inconsistent across task types.

## Decision

Adopt **Task Execution** as a deep Module with this domain model:

```text
Goal
  -> Run
     -> Step graph
        -> Action
        -> Event
        -> Artifact
        -> Approval
```

- A Goal is user intent and may have multiple Runs.
- A Run is one durable execution attempt and can be queued, running, paused, waiting for approval, completed, failed, or cancelled.
- A Step is a node in a dependency graph. Readiness is derived from completed dependencies rather than array position.
- A Run has exactly two user-facing completion modes: `manual` and `assisted`.
- In manual mode, the user completes the Step directly.
- In assisted mode, the user submits evidence; the AI returns a durable passed, revision-requested, or unavailable review. AI review must never silently complete a Step on the user's behalf.
- When assisted review is unavailable, evidence remains stored as an Action and Artifact while the Step stays open for a later retry or user revision.
- Actions record auditable work, Events are append-only execution history, Artifacts are reviewable outputs, and Approvals are explicit durable decisions.
- State changes use compare-and-set persistence so stale callers cannot silently overwrite newer execution state.

The public contracts use `/api/goals`, `/api/runs`, `/api/approvals`, and `/api/triggers`. Run and Step progress uses explicit state-transition endpoints such as start, pause, complete, review, retry, and cancel. The old `/api/tasks` and `/api/task-chains` routes are retired; no runtime compatibility module or legacy task persistence remains. Advisor behavior is independently exposed through its current conversation and planning contracts.

Task Execution has no task Worker Lease, Heartbeat, Checkpoint, or Run Command lifecycle. Those mechanisms are reserved for durable backend Jobs such as plan generation and knowledge ingestion, not ordinary user actions.

## Consequences

- A standalone task becomes a Goal with a one-Step Run.
- A former task chain becomes one Run with a Step dependency graph.
- A recurring or event-based need becomes a Trigger that creates an ordinary Run; it does not create a separate automatic-task execution system.
- Planning produces a draft Run specification instead of choosing between `single_task` and `workflow_chain` architectures.
- Frontends can present simple task views without losing execution history, evidence, review, or recovery state.
- Existing task data is migrated through verified one-time retirement migrations. The migration aborts rather than deleting data if a task or reward cannot be mapped to canonical records.

## Migration Status

1. Completed: Task Execution tables, Module Interface, versioned HTTP contracts, atomic state transitions and Events, and dependency readiness.
2. Completed: planning produces reviewable Run specifications while keeping the user-facing planning flow independent from task-model internals.
3. Completed: migration 10 stages historical tasks and chains as canonical Goals, Runs, Steps, Events, and Approvals.
4. Completed: migration 11 links Reward Settlement to canonical Run/Step identity.
5. Completed: migration 12 replaces automatic-task execution with Trigger-to-Run automation.
6. Completed: Goal editing/status lifecycle, explicit Step skipping, and Trigger edit/delete management close the user-facing execution surface.
7. Completed: migration 23 verifies legacy mappings, repairs canonical reward links, and retires legacy routes, repositories, projections, and tables. Historical projection code is migration-only and cannot serve runtime requests.
8. Completed: migrations 24 and 25 permanently normalize object-shaped Task Execution JSON fields and install database constraints that reject malformed future writes.
9. Completed: migrations 34 and 35 unify assisted execution and retire Run Commands. New writes use only manual or assisted execution; historical agent data is read only for one-time normalization where required.
10. Completed: runtime startup and health checks reject missing, renamed, discontinuous, or newer migration histories instead of serving against an unknown schema.

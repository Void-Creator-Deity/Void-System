# ADR-0006: Goal, Run, and Step Task Execution

- Status: Accepted, backend implemented
- Date: 2026-07-15

## Context

The original task system models standalone tasks, automatic tasks, and task chains as different product concepts. Execution state is spread across `tasks`, `task_chains`, prerequisite JSON, planning code, HTTP routes, and reward logic. The model can represent a linear checklist, but it has no durable Run lifecycle, append-only history, approval state, retry attempt, artifact record, or reliable parallel Step graph.

This makes background agent work difficult to pause, resume, steer, inspect, or migrate to another product shell. It also forces clients to understand implementation details such as chain generation and completion types.

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
- Manual work, assisted work, and agent work use the same Run model. Mode affects execution policy, not persistence architecture.
- Actions record individual manual, agent, or tool operations.
- Events are append-only and provide the audit and resume history.
- Artifacts are first-class reviewable outputs.
- Approvals are explicit durable decisions, not chat messages or transient callbacks.
- State changes use compare-and-set persistence so stale callers cannot silently overwrite newer execution state.

The new public contracts use `/api/goals`, `/api/runs`, and command endpoints on Runs and Steps. Existing `/api/tasks`, `/api/task-chains`, and `/api/ai/advisor` paths remain available through compatibility Modules during staged migration. They must not gain new core behavior.

## Consequences

- A standalone task becomes a Goal with a one-Step Run.
- A former task chain becomes one Run with a Step dependency graph.
- "Automatic task" becomes an agent-mode Run that can still pause, await approval, and be reviewed.
- Planning produces a draft Run specification instead of choosing between `single_task` and `workflow_chain` architectures.
- Frontends can present simple task views without losing execution history or advanced controls.
- Existing task data needs an explicit backfill/projection migration before the legacy tables can be retired.

## Migration Status

1. Completed: Task Execution tables, Module Interface, versioned HTTP contracts, atomic state/Event commands, and dependency readiness.
2. Completed: planning produces reviewable Run specifications while preserving advisor response compatibility.
3. Completed: migration 9 adds renewable Worker Leases and durable Checkpoints for agent execution.
4. Completed: migration 10 backfills legacy tasks and chains and atomically projects legacy writes into canonical Goals, Runs, Steps, Events, and Approvals.
5. Completed: migration 11 links Reward Settlement to canonical Run/Step identity while preserving legacy task compatibility.
6. Completed: migration 12 replaces automatic-task execution with Trigger-to-Run automation and durable Run Commands.
7. Completed: Goal editing/status lifecycle, explicit Step skipping, and Trigger edit/delete management close the user-facing command surface.
8. Pending: switch the frontend to Goal, Run, Trigger, and Run Command clients while retaining simple task-oriented presentation.
9. Pending: audit migrated data and retire legacy task persistence after the frontend no longer depends on it.

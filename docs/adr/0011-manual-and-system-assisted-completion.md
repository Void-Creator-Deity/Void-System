# ADR-0011: Manual and System-Assisted Completion

- Status: Accepted
- Date: 2026-07-20
- Supersedes in part: ADR-0006 and ADR-0007

## Context

The original Task Execution model correctly consolidated historical standalone tasks, task chains, and automatic tasks into Goal, Run, Step, Action, Event, Artifact, and Approval records. However, the current product exposes three execution modes: `manual`, `assisted`, and `agent`.

Only manual completion has an end-to-end user path. Assisted work is currently stored as a label but is completed through the same direct command. Agent work has leases and checkpoints but no first-party worker that can safely invoke tools, publish progress, recover from failure, request approvals, or produce audited artifacts. Presenting these as equivalent choices is misleading.

## Decision

The current product exposes exactly two Run modes:

1. `manual` (user-facing: **自己完成**): the user may record output and artifacts, then directly mark a running Step complete.
2. `assisted` (user-facing: **系统协助**): the user works on the Step, submits output and artifacts to the system companion, and receives a persisted review result. A passing review completes the Step. A revision request or AI failure leaves the Step running and retains the evidence for review or retry.

The system companion is available for questions in both modes. Conversational help never changes a Step state by itself.

`agent` is not an active product mode. Migration converts existing agent Runs to assisted Runs and agent Step kinds to manual Step kinds. The first-party worker-lease HTTP endpoints, Module methods, repository surface, and lease table are removed in the same replacement migration. A future automatic-execution capability requires a new ADR and a complete vertical slice: durable Job ownership, least-privilege tools, approval scopes, live progress, cancellation, retry/recovery, artifacts, and audit events.

## Consequences

- The canonical execution graph remains Goal -> Run -> Step -> Action/Event/Artifact/Approval. No new task architecture is introduced.
- System-assisted review is an Action with durable input, normalized model output, and an append-only Event. The latest review is returned in the authoritative Run snapshot so it survives refresh.
- An unavailable or invalid evaluator is an explicit retryable result, never a direct completion, hidden fallback, or failure of the user’s work.
- Existing automatic-run data is preserved as historical assisted work. No runtime compatibility route remains after migration.
- ADR-0007 remains historical evidence for the retired lease implementation, but it is no longer part of the current runtime contract.

# ADR-0008: Trigger-to-Run Automation

- Status: Accepted, backend implemented
- Date: 2026-07-15

## Context

The original product treats automatic tasks as a separate execution architecture. Schedule delivery, external events, retries, and Run creation therefore risk becoming provider-specific route logic or process-local state.

Task Execution already owns canonical Goal, Run, Step, Action, Event, Artifact, and Approval lifecycles. Automation must enter that model without duplicating it or introducing a hidden execution path.

## Decision

Adopt **Task Automation** as a deep Module with two concepts:

- A **Trigger** is an active or paused schedule/event rule that owns a Goal and a validated Run template.
- A **Trigger Firing** maps one stable external source key to one canonical Run.

Trigger firing creates a Run through Task Execution with a deterministic, bounded idempotency key derived from the Trigger and source key. The Firing is then recorded with a `trigger.fired` Event in one transaction. If a process stops after Run creation but before recording the Firing, retrying reuses the same Run and completes the record without duplicate execution.

Scheduler, queue, webhook, and integration implementations remain Adapters. They decide when to call the Trigger Interface but do not own execution state. HTTP routes translate transport and errors only.

A Trigger only creates a Run. Once the Run exists, people advance it through its explicit state transitions, evidence submission, review, and retrospective. A change of direction is represented by cancelling, finishing, or reviewing the current Run and creating a follow-up Run; the system has no hidden instruction queue for an active Run.

## Consequences

- "Automatic task" is retired as an execution architecture; it becomes a Trigger that creates an ordinary Run.
- Schedule providers and event sources can change without changing Task Execution persistence.
- At-least-once delivery does not create duplicate Runs when callers preserve the source key.
- Trigger templates are validated before storage, so invalid dependency graphs fail at configuration time rather than during background delivery.
- Trigger lifecycle includes validated edits, pause/resume, and owner-scoped deletion; existing Runs remain durable after a Trigger is removed.
- The backend exposes Trigger contracts; first-party screens translate schedules into product language and do not expose scheduler implementation details.

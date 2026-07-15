# ADR-0008: Trigger-to-Run Automation and Durable Steering

- Status: Accepted, backend implemented
- Date: 2026-07-15

## Context

The original product treats automatic tasks as a separate execution architecture and has no durable way to deliver a follow-up instruction to an active agent. Schedule delivery, external events, retries, Run creation, and worker input therefore risk becoming provider-specific route logic or process-local state.

Task Execution already owns the canonical Goal, Run, Step, Action, Event, Artifact, Approval, Worker Lease, and Checkpoint lifecycles. Automation needs to enter and steer that model without duplicating it.

## Decision

Adopt **Task Automation** as a deep Module with two concepts:

- A **Trigger** is an active or paused schedule/event rule that owns a Goal and a validated Run template.
- A **Trigger Firing** maps one stable external source key to one canonical Run.
- A **Run Command** is a durable instruction or follow-up for a nonterminal Run. Workers list pending commands and acknowledge them after incorporation.

Trigger firing creates a Run through Task Execution with a deterministic, bounded idempotency key derived from the Trigger and source key. The Firing is then recorded with a `trigger.fired` Event in one transaction. If a process stops after Run creation but before recording the Firing, retrying reuses the same Run and completes the record without duplicate execution.

Run Command creation and its `run.command_added` Event are atomic. Acknowledgement and its `run.command_acknowledged` Event are also atomic and idempotent.

Scheduler, queue, webhook, and integration implementations remain Adapters. They decide when to call the Trigger Interface but do not own execution state. HTTP routes translate transport and errors only.

## Consequences

- "Automatic task" is retired as an execution architecture; it becomes a Trigger that creates an ordinary Run.
- Schedule providers and event sources can change without changing Task Execution persistence.
- At-least-once delivery does not create duplicate Runs when callers preserve the source key.
- Agent workers can receive user corrections and follow-up requests after a Run starts without relying on chat-session memory.
- Trigger templates are validated before storage, so invalid dependency graphs fail at configuration time rather than during background delivery.
- Trigger lifecycle includes validated edits, pause/resume, and owner-scoped deletion; existing Runs remain durable after a Trigger is removed.
- The backend now exposes Trigger and Run Command contracts; the frontend still needs friendly schedule controls and Run steering views.

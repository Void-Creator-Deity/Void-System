# ADR-0007: Agent Worker Leases and Checkpoints

- Status: Accepted, backend implemented
- Date: 2026-07-15

## Context

Agent Runs can outlive one request or process. Process-local ownership cannot prevent two workers from advancing the same Run, and an interrupted worker needs durable resume state. A queue delivery alone is insufficient because delivery, execution ownership, and Run state have different lifecycles.

## Decision

Store one renewable Worker Lease per Run in the Task Execution Adapter.

- A claim records worker identity, a secret lease token, acquisition time, heartbeat time, expiry, version, and structured checkpoint data.
- An active lease excludes other workers. An expired lease can be reclaimed and receives a new token.
- Heartbeats renew expiry and may atomically replace checkpoint data.
- Release records the final checkpoint and makes ownership inactive.
- Stale or foreign tokens are rejected.
- Lease claims, reclaims, checkpoints, and releases emit append-only Events.
- Public Run snapshots may expose worker identity and expiry but never the lease token.

## Consequences

- Agent execution can resume after worker loss without relying on process memory.
- Queue or scheduler Adapters can change without changing Run persistence.
- Workers must treat the lease token as a short-lived secret and checkpoint before risky or long operations.
- Future steering and follow-up commands can target durable Runs instead of transient worker sessions.

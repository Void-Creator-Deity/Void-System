# Project Context

## Product

Void System is a personal growth workspace. It turns goals and personal knowledge into plans, tasks, evidence, evaluations, and measurable progress. Product-facing language should be calm and practical; implementation terms such as RAG, vectors, chains, prompts, providers, and database fields belong in advanced administration views, not primary user workflows.

## Domain Language

- **Workspace Core**: portable contracts and domain rules that can support this product or another product shell.
- **Growth App**: the current user-facing product assembled on top of Workspace Core.
- **Knowledge Engine**: ingestion, indexing, retrieval, reranking, grounded answering, citations, and index lifecycle. RAG is one implementation technique, not the product concept.
- **Planning Engine**: converts a goal and user capabilities into a reviewable task plan.
- **Goal**: a durable statement of user intent. A Goal is lightweight and can have many execution attempts.
- **Run**: one resumable execution attempt for a Goal. A Run owns lifecycle, mode, checkpoints, and its Step graph.
- **Step**: a unit of work inside a Run. Steps can depend on other Steps, run serially or in parallel, retry, await Approval, and produce Artifacts.
- **Action**: one manual, agent, or tool operation performed for a Step. Actions are auditable execution records, not a separate task type.
- **Event**: an append-only record of a meaningful Run or Step transition.
- **Artifact**: a reviewable result produced by a Run or Step, such as text, a file, a link, or structured output.
- **Approval**: an explicit human decision that allows a paused Step to continue or rejects it.
- **Worker Lease**: renewable, exclusive ownership of an agent-mode Run by one worker. Expired leases can be reclaimed without trusting process memory.
- **Checkpoint**: durable, structured resume data saved while a Worker Lease is active.
- **Trigger**: a durable schedule or external event rule that creates a Run from a validated template. A Trigger is an entry condition, not a separate task type.
- **Trigger Firing**: the idempotent record connecting one stable external source key to the canonical Run it created.
- **Run Command**: a durable instruction or follow-up submitted to a nonterminal Run and acknowledged by a worker after it has incorporated the input.
- **Task Automation**: owns Trigger lifecycle, idempotent Trigger Firing, and durable Run Commands while delegating all execution state to Task Execution.
- **Task Execution**: owns Goal, Run, Step, Action, Event, Artifact, and Approval lifecycle rules, including dependency readiness, pause/resume, retry, cancellation, evidence, evaluation, and reward settlement.
- **Task Workflow**: compatibility language for the legacy task endpoints. New backend behavior belongs to Task Execution.
- **Capability**: a user attribute or skill that planning and rewards may reference.
- **Reward Settlement**: the one-time, atomic application of coins, experience, and capability growth for a completed task.
- **Profile Observation**: user-owned, traceable evidence such as a review event or aggregate action pattern. It is not a personality conclusion.
- **Profile Claim**: a reviewable candidate understanding supported by one or more Profile Observations.
- **User Override**: a user's confirmation, correction, rejection, or reset of a Profile Claim. It takes precedence over system inference.
- **Behavior Insight**: an aggregate, first-party task-history pattern presented for review; it never silently becomes a profile fact.
- **Legacy Adapter**: an implementation that lets a new Core interface use existing database, Chroma, document, or advisor code during migration.

## Architectural Invariants

1. HTTP routes translate transport data and errors; they do not own domain rules.
2. Reward Settlement is atomic and idempotent per user and completed work item.
3. Step dependencies and valid state transitions are enforced by Task Execution for every relevant entry point.
4. Knowledge Engine callers depend on portable contracts, not Chroma or a specific LLM framework.
5. Planning and evaluation callers depend on engine contracts, not advisor-chain functions.
6. Existing public API paths remain compatible during staged migration unless a versioned replacement is introduced.
7. Product configuration exposes user intent first; provider and storage details belong to advanced administration.
8. Standalone, generated, scheduled, and agent-operated work are Run modes or presentation choices, not separate task architectures.
9. Every meaningful Run and Step transition emits an append-only Event; resumability must not depend on process memory.
10. Agent workers must hold a valid renewable Worker Lease before advancing a Run, and must persist resumable Checkpoints through the Adapter.
11. Legacy task and task-chain writes are compatibility projections into Task Execution, never an independent source of execution truth.
12. Schedules and external events create Runs through durable Triggers; they never introduce another execution model.
13. User steering and follow-up input are durable Run Commands with append-only Events, not transient chat callbacks or process-local queues.
14. The initial portrait system uses only first-party Workspace evidence, exposes reviewable non-clinical behavior insights, and never auto-writes an effective profile without a user decision.

## Migration Direction

The codebase now uses deep domain modules and portable Core interfaces as the canonical architecture. New behavior must be added behind those interfaces. Existing implementations may remain behind Legacy Adapters during explicit deprecation windows, but they are compatibility surfaces rather than independent sources of truth. Router ownership is split across tasks, knowledge, planning, identity, conversations, personal context, growth, and administration.

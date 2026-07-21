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
- **Action**: one user, system-review, or tool operation performed for a Step. Actions are auditable execution records, not a separate task type.
- **Event**: an append-only record of a meaningful Run or Step transition.
- **Artifact**: a reviewable result produced by a Run or Step, such as text, a file, a link, or structured output.
- **Approval**: an explicit human decision that allows a paused Step to continue or rejects it.
- **Trigger**: a durable schedule or external event rule that creates a Run from a validated template. A Trigger is an entry condition, not a separate task type.
- **Trigger Firing**: the idempotent record connecting one stable external source key to the canonical Run it created.
- **Run Command**: a durable instruction or follow-up submitted to a nonterminal Run and acknowledged by a worker after it has incorporated the input.
- **Task Automation**: owns Trigger lifecycle, idempotent Trigger Firing, and durable Run Commands while delegating all execution state to Task Execution.
- **Task Execution**: owns Goal, Run, Step, Action, Event, Artifact, and Approval lifecycle rules, including dependency readiness, pause/resume, retry, cancellation, evidence, evaluation, and reward settlement.
- **Capability**: a user attribute or skill that planning and rewards may reference.
- **Reward Settlement**: the one-time, atomic record of predeclared growth points for a completed Step. It neither spends points nor changes capabilities automatically.
- **Profile Observation**: user-owned, traceable evidence such as a review event or aggregate action pattern. It is not a personality conclusion.
- **Profile Claim**: a reviewable candidate understanding supported by one or more Profile Observations.
- **User Override**: a user's confirmation, correction, rejection, or reset of a Profile Claim. It takes precedence over system inference.
- **Behavior Insight**: an aggregate, first-party task-history pattern presented for review; it never silently becomes a profile fact.
- **Plan Draft**: a persistent, user-reviewable Goal and Run specification produced by Planning before publication; it is not executable until an idempotent publish use case creates the canonical Goal and Run.
- **Durable Job**: a persisted long-running operation with owner, lifecycle, stage, progress, attempts, result, structured failure, cancellation, and worker ownership that survives browser and process restarts.
- **Context Compiler**: the permissioned selector that assembles purpose-specific AI context under provenance, freshness, sensitivity, and token budgets.
- **Model Connection Profile**: the normalized provider, base URL, credential reference, model, timeout, retry, streaming, and capability configuration shared by discovery, testing, and runtime calls.
- **Legacy Adapter**: a temporary implementation used only behind a current Core interface for a named, time-bounded migration. Legacy Task Execution code is excluded from this term because it is retained only as one-way database migration code.

## Architectural Invariants

1. HTTP routes translate transport data and errors; they do not own domain rules.
2. Reward Settlement is atomic and idempotent per user and completed work item.
3. Step dependencies and valid state transitions are enforced by Task Execution for every relevant entry point.
4. Knowledge Engine callers depend on portable contracts, not Chroma or a specific LLM framework.
5. Planning and evaluation callers depend on engine contracts, not advisor-chain functions.
6. Public API changes use an explicit replacement and retirement decision; retired task APIs must not remain as hidden runtime compatibility surfaces.
7. Product configuration exposes user intent first; provider and storage details belong to advanced administration.
8. Standalone, generated, and scheduled work share the same Run model. Current user-facing completion modes are manual and system-assisted; future automatic work requires a separately accepted complete worker architecture.
9. Every meaningful Run and Step transition emits an append-only Event; resumability must not depend on process memory.
11. Historical task and task-chain records are converted once by ordered database migrations; no runtime route, repository, or domain Module may read or write the retired model.
12. Schedules and external events create Runs through durable Triggers; they never introduce another execution model.
13. User steering and follow-up input are durable Run Commands with append-only Events, not transient chat callbacks or process-local queues.
14. The initial portrait system uses only first-party Workspace evidence, exposes reviewable non-clinical behavior insights, and never auto-writes an effective profile without a user decision.
15. Migration-only code is one-way, isolated from runtime composition, and removable after the oldest supported database version no longer needs it.
16. Runtime startup succeeds only when recorded SQLite migration history is a contiguous, name-matching prefix of the current Schema Contract and the database reaches the current version.
17. Object-shaped Task Execution JSON fields are permanently normalized during migration and enforced as JSON objects by database constraints.
18. Long-running model, indexing, and import operations use Durable Jobs whose authoritative state survives page refresh and process restart; process-local background tasks may dispatch work but cannot be the recovery contract. Future automatic task execution must meet this invariant before it is exposed.
19. Model discovery, connection verification, and runtime generation use the same Model Connection Profile and capability-aware Adapter path.
20. A product capability is incomplete until every applicable Domain, Module, Adapter, Schema, HTTP, frontend client, UI recovery, test, and ACTIVE-document layer is implemented and verified.

## Migration Direction

The codebase uses deep domain Modules and portable Core interfaces as the canonical architecture. New behavior must be added behind those interfaces. A Legacy Adapter is allowed only during an explicit, time-bounded migration and must not preserve a retired public contract indefinitely. Historical Task Execution conversion lives under migration support and is never composed into HTTP or domain runtime paths. Router ownership is split across tasks, knowledge, planning, identity, conversations, personal context, growth, and administration.

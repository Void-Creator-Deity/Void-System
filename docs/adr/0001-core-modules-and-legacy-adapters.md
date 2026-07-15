# ADR-0001: Core Modules With Legacy Adapters

- Status: Accepted
- Date: 2026-07-12

## Context

The backend concentrated HTTP routing, task rules, AI orchestration, knowledge retrieval, configuration, and persistence in a few very large files. Product behavior was difficult to test without FastAPI, SQLite, Chroma, and model dependencies. The current knowledge implementation is useful but represents a basic retrieval pipeline rather than a complete Knowledge Engine.

## Decision

Adopt a staged **Workspace Core + deep Modules + Adapters** architecture.

- core defines portable interfaces, data contracts, invariants, and expected error modes.
- modules implements product behavior behind small interfaces.
- adapters/legacy connects those interfaces to current SQLite, Chroma, document, and advisor implementations.
- HTTP routes preserve existing paths while delegating behavior to Modules.
- New persistence behavior that spans multiple records must provide an atomic Adapter operation.

The first Modules are Knowledge Engine, Planning Engine, and Task Workflow. Task reward completion uses a unique settlement ledger and a single SQLite transaction.

## Consequences

- Domain behavior can be tested without importing FastAPI or model libraries.
- Replacing Chroma, an LLM provider, the advisor chain, or SQLite no longer requires editing route logic.
- During migration, some Legacy Adapters may temporarily duplicate work; this is accepted only when called out and scheduled for removal.
- main.py remains large until routers are extracted, but migrated routes must not regain domain logic.
- A second Adapter is required before claiming a seam is proven portable in production; fake Adapters establish the test surface but not operational portability.

## Next Decisions

1. Router ownership and dependency composition outside main.py.
2. Knowledge index versioning, hybrid retrieval, reranking, citation validation, and evaluation datasets.
3. A migration path from the current monolithic Database class to domain repositories and explicit migrations.
4. Versioned public API contracts for a reusable Workspace Core product shell.

# ADR-0003: Application Composition and Focused SQLite Adapters

- Status: Accepted
- Date: 2026-07-12

## Context

The Growth App assembled response models, authentication dependencies, application resources, and domain routes inside `main.py`. Migrated Task Workflow routes still reached persistence through the monolithic `Database` class, so the `TaskRepository` seam was portable in tests but not in runtime composition.

## Decision

- Put shared HTTP response contracts and authentication dependencies under `api/http`.
- Store application-owned adapters on `app.state` during FastAPI lifespan instead of module-level globals.
- Extract routes only after their domain rules live in a deep Module; routers remain transport Adapters.
- Implement `SQLiteTaskRepository` directly against a connection factory and compose Task Workflow with it.
- Keep legacy `Database` methods as temporary compatibility facades that delegate migrated write behavior to focused SQLite Adapters.

## Consequences

- Task Workflow runtime composition now uses the same small interface exercised by its tests.
- Router modules can be moved into another product shell without importing `main.py`.
- Application startup and tests can replace the database Adapter through FastAPI dependency overrides or application state.
- The monolithic `Database` class remains during staged migration, but migrated behavior must not add new SQL there.
- Full route integration tests still require a repaired backend environment with FastAPI dependencies installed.

## Next Decisions

1. Extract identity, planning, document ingestion, and conversation routers by domain ownership.
2. Move schema creation from `Database.init_database` to ordered migrations.
3. Introduce focused SQLite Adapters for identity, capabilities, conversations, and administration.
4. Define versioned Workspace Core HTTP contracts separately from legacy Growth App paths.

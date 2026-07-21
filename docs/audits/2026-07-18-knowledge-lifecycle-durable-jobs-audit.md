# 2026-07-18 Knowledge Lifecycle Durable Jobs Audit

- Status: IMPLEMENTED - automated verification complete; browser acceptance pending
- Scope: Personal knowledge upload, parsing, indexing, rebuilding, recovery, and the document-library progress experience.
- Design sources: DESIGN.md sections 4 and 15; PROJECT_RULES.md sections 2, 3, 4, and 12; CONTEXT.md invariants 4, 18, and 20; ADR-0001, ADR-0004, and ADR-0005.

## Original Problem

The original implementation had persisted ingestion outcome records but no durable execution ownership. Upload processing could be launched from an in-process coroutine and rebuild work could be delegated to request-process background execution. Those mechanisms did not make SQLite the lifecycle authority, could not safely recover after restart, and gave the document page no durable owner-visible progress, cancellation, or retry control.

This audit was opened to replace those paths rather than layering a second progress display over them.

## Implemented Canonical Path

upload or rebuild request -> persisted knowledge job -> lease-aware worker -> parse/index adapter -> authoritative job/document state -> document library and global progress recovery

The replacement path is now the only production lifecycle path:

| Layer | Implemented behavior |
| --- | --- |
| Domain contract | `KnowledgeJobService` owns owner-scoped job creation, reading, listing, cancellation, retry, and leased execution. |
| Module | Upload creates one durable job for a persisted source document; rebuild creates an owner-scoped batch job. |
| Adapter | `SQLiteKnowledgeLifecycleRepository` owns transactional claim, heartbeat, completion, failure, cancellation, retry, and interrupted-job recovery. |
| Schema | Migration 28 extends the durable job record with work type, request payload, attempts, cancellation request, worker identity, lease token/expiry, heartbeat, progress, and result fields. |
| Runtime | FastAPI lifespan first recovers interrupted work, then starts an application worker that can only mutate a job while holding its lease. |
| HTTP/OpenAPI | Upload and rebuild return authoritative job snapshots. Owner-scoped list, get, cancel, and retry endpoints expose the same stored lifecycle. |
| Frontend | The document library and shared background-progress client restore work from server snapshots after refresh and expose terminal failure, cancellation, and retry. |
| State semantics | A cancelled job now leaves its source document in `cancelled`, not `failed`; the document library renders `已取消` with a retry-oriented explanation. |

A job uses `queued`, `processing`, `cancelling`, `completed`, `failed`, or `cancelled`. The public snapshot contains bounded stage/progress information but no provider credentials, prompts, raw source content, or private lease token. Retrying creates a new job against the same validated source document rather than rewriting a terminal record.

## Retired Paths

- Direct `asyncio.create_task(...)` ingestion from `UserDocumentManager` runtime behavior is retired.
- FastAPI `BackgroundTasks` from `POST /api/user/documents/rebuild-index` is retired.
- The lifecycle repository historical `update_ingestion(...)` escape hatch is deleted; finalization must go through the worker lease.
- Frontend completion no longer relies on a submit response as proof that parsing or indexing finished.

Legacy parser and vector implementation details may remain behind maintenance adapters, but they no longer own lifecycle state or background-work recovery.

## Automated Verification Completed

The focused knowledge lifecycle suite verifies:

1. Migration from a version-27 database and recovery of queued, processing, and cancelling jobs.
2. Owner isolation, idempotent submission, lease contention, cancellation, retry, failure, and completed results.
3. A job can complete only through the worker currently holding its lease.
4. A worker checkpoint that observes a cancellation request records both the job and document as `cancelled`.
5. Upload/rebuild HTTP snapshots and owner-scoped get/list/cancel/retry behavior.
6. Frontend background-work refresh recovery, terminal failure, cancellation, and retry handling.
7. Production frontend build and targeted backend module, adapter, HTTP, and migration tests.

Latest automated completion run: 209 backend tests and 28 frontend tests passed. The commands are reproducible from the repository root:

- Backend: `cd void-system-backend; & .\.venv313\Scripts\python.exe -m unittest discover -s tests -v`
- Frontend tests: `cd void-system-frontend; node --test tests/*.test.js`
- Frontend build: `cd void-system-frontend; & .\node_modules\.bin\vite.cmd build`

The backend command uses the repository-local Python environment (`void-system-backend/.venv313`) and does not depend on a global `uv` or Python install.

## Remaining Manual Browser Acceptance

Automated verification does not replace a live browser check against the user BAT-started services. This audit is not fully accepted until the following flow is observed:

1. Upload a small `.txt` document from the library.
2. Refresh or leave and return to the library while work is active; the same job and its progress must reappear.
3. Cancel an active job; background progress and the document card must both show `已取消`.
4. Retry from the background-task entry; a new job must appear and complete.
5. Confirm the document reaches the queryable state and is retrievable through the normal knowledge-question flow.

Any mismatch in that flow must be treated as a lifecycle defect in the canonical path, not hidden with page-local state or a compatibility fallback.

## Non-goals

This batch does not silently change the configured model, user account, user source data, or retention policy. It does not claim that parser/vector adapters are interchangeable before a second operational adapter exists. System/shared knowledge repair remains separately scoped because its ownership, maintenance surface, and content source differ from personal knowledge ingestion.

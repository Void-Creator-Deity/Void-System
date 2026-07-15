# ADR-0005: Personal Knowledge Retention and Retrieval Eligibility

- Status: Accepted
- Date: 2026-07-15

## Context

Personal knowledge documents previously used one destructive delete operation. It removed indexed chunks before deleting metadata and the source file. A later database failure could therefore leave a visible document that no longer supported answers. The same endpoint also gave people no reversible way to remove an item from their active workspace.

Retrieval adapters queried the user collection directly, so document lifecycle state could not reliably prevent retained or disabled content from being cited.

## Decision

Introduce a Personal Knowledge Workspace module with a focused SQLite repository and an explicit retention policy:

1. Active documents are visible and eligible for retrieval.
2. Archiving is the default delete behavior. It is reversible and immediately removes the document from every retrieval candidate set.
3. Restoring re-enables the retained source and its existing indexed content.
4. Permanent purge is a separate operation available only for archived documents. Indexed chunks are removed before metadata and the source file. If index cleanup fails, archived metadata remains intact and the operation can be retried.
5. Semantic and lexical retrieval adapters obtain eligible document IDs from the repository before querying the current index implementation.
6. HTTP routers depend on `KnowledgeWorkspace`, not the legacy document manager, vector manager, or the `Database` facade.
7. Metadata browsing, statistics, retention, and recent activity compose without importing parser, model, or vector-store dependencies. Maintenance and retrieval infrastructure is loaded only when those capabilities are invoked.

SQLite migration 7 adds `user_documents.is_active`, `user_documents.archived_at`, and an owner-retention index. The current parser and Chroma implementation remain Legacy Adapters behind the module boundary.

## Consequences

- A normal remove action no longer destroys a user source material.
- Archived material cannot leak back into grounded answers.
- Permanent deletion failures preserve a consistent, retryable state.
- Frontends can offer active and recycle-bin views without understanding index internals.
- Opening the workspace remains available when optional retrieval infrastructure is disabled, unavailable, or being repaired.
- Existing `DELETE /api/user/documents/{id}` clients remain transport-compatible, but its product meaning is now archive rather than irreversible deletion.

## Follow-up

1. Add document replacement against the existing version records.
2. Add scheduled purge policies for workspaces that opt into automatic retention cleanup.
3. Replace the current active-ID filtering strategy with a scalable catalog-aware index Adapter when document volume requires it.

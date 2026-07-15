# ADR-0004: Knowledge Engine Lifecycle and User Activity

- Status: Accepted
- Date: 2026-07-14

## Context

The Knowledge Engine already retrieves, ranks, and cites material, but the Growth App could not tell a person whether a newly added document was queued, being prepared, complete, or failed. It also lacked a durable record of which sources supported recent answers. This made failure recovery, trust, and future quality evaluation difficult.

The existing user document and legacy index APIs remain active and must stay compatible during migration.

## Decision

Add a focused SQLite Adapter that owns three durable records:

1. A document version captures the content fingerprint, source size, and index version for each uploaded document.
2. An ingestion job records queued, processing, completed, or failed preparation work, including document chunk count and a bounded failure message.
3. A retrieval trace records the user-owned question, selected source references, and evidence counts after citation validation.

Document list and detail responses attach a compact knowledge_status object so the Growth App can show useful preparation feedback. GET /api/user/knowledge/activity provides recent question-and-source activity in product language. It intentionally omits storage, provider, prompt, and index internals.

Trace persistence is best-effort: an answer remains available when activity recording is temporarily unavailable. All lifecycle reads and writes include the owner identifier.

## Consequences

- People can understand whether a document is ready to support their work.
- Knowledge activity can show sources used by recent answers without exposing implementation details.
- Document versioning and retrieval traces create the foundation for re-indexing, evaluation datasets, quality monitoring, and retention controls.
- The legacy document and index adapters remain in place, but new lifecycle SQL is isolated in a focused Adapter rather than expanding the legacy Database facade.

## Follow-up

1. Add document replacement against the existing version records. Retention controls are delivered by ADR-0005.
2. Add curated evaluation cases and evaluation runs before calibrating answer quality.
3. Replace the legacy index with independently scalable semantic and lexical Adapters when workspace size requires it.

# 2026-07-18 Private Knowledge At-Rest Encryption Audit

- Status: Implemented and verified against the active local data on 2026-07-18
- Scope: Private managed source files, SQLite content previews, and personal Chroma document bodies.
- Design sources: DESIGN.md sections 4, 6, and 17; PROJECT_RULES.md sections 3, 4, 11, and 12; ADR-0005 and ADR-0009.

## Evidence and Root Cause

The unified library preserved owner filters at API and retrieval boundaries, but its private source bytes, extracted preview, and Chroma `documents` value were persisted as plaintext. Authorization alone does not protect a copied SQLite database, a readable vector directory, or a managed upload directory. In addition, module-local construction could create a catalog without the runtime cipher even where the main application composition injected one.

## Canonical Path

private upload -> Fernet-encrypted managed source -> durable parse/index job -> plaintext only in trusted worker memory -> plaintext embedding -> Fernet-encrypted Chroma document body -> owner-scoped catalog eligibility -> trusted server decryption -> authorized answer or preview

The canonical cipher is created from RuntimeSettings and injected into the personal document manager, private catalog, user workspace catalog, and Chroma store. The source and index encryption versions are persisted separately so restart recovery can determine exactly which content copy still needs migration.

## Affected Layers

| Layer | Implementation | Verification |
| --- | --- | --- |
| Core/security boundary | KnowledgeSourceCipher owns key validation, Fernet content encryption, and one-time retired-key relocation | unit regression and production-key configuration review |
| Domain module | PersonalKnowledgeDocumentManager encrypts new sources and performs source/index migration orchestration | source encryption and migration tests |
| SQLite adapter | Private preview is encrypted; owner-filtered reads reveal plaintext only in process | repository integration test |
| Chroma adapter | Private bodies are encrypted, metadata is minimized, authorized retrieval decrypts in process | Chroma regression test |
| Schema | Migration 30 records index encryption version and adds migration query support | migration suite |
| Application composition | startup source migration and durable index rebuild queue use one cipher source | startup smoke test |
| User interface | no new UI controls; existing library continues to receive authorized plaintext only | library browser regression |

## Retirement and Migration

- Retire plaintext writes for new private source files, previews, and Chroma document bodies.
- Migrate historical private SQLite previews before library reads; an unmigrated private preview is hidden rather than returned as plaintext.
- Migrate every historical private source to an opaque `<document_id>.bin` path, validate ciphertext first, and update the source version and SQLite path together.
- Replace historical plaintext Chroma bodies through the existing durable job path. Delete the old plaintext chunks before queueing the encrypted rebuild; a broken embedding provider leaves the document temporarily unavailable rather than preserving a sensitive plaintext index.
- Do not keep a permanent plaintext compatibility read path. The retired development key is moved once to the canonical key location, then the old path is removed.

## Verification Completed

- The project-managed Python 3.13 environment passed the SQLite migration, private encryption migration, private encryption, document-manager, Chroma migration, resource, and workspace suites: 25 tests total.
- The active private catalog was migrated in place: encrypted source, encrypted preview, encrypted Chroma bodies, and no remaining source/index migration candidates.
- The historical source path now ends in opaque `.bin`; the original filename no longer appears in the managed path or private Chroma metadata.
- Raw private Chroma bodies do not contain the checked source fragment, while owner-authorized semantic and lexical retrieval both decrypt and return parsed text in process.
- Chroma client cleanup is explicit for Windows so isolated stores do not retain vector-file handles after their runtime ends.

The checked-in Python virtual environment points at a missing CPython 3.12.9 interpreter and the current shell has no working `uv`. Deterministic Python compilation and SQLite migration tests have passed, but the dependency-backed Chroma regression suite cannot be honestly reported as passed until the project environment is restored.

## Non-goals

This batch does not claim encrypted SQLite files, encrypted embeddings, encrypted metadata, automatic key rotation, or a change in official/shared material access semantics. It does not upload keys, modify a real account, or change user data except when the application performs the documented private-content migration.

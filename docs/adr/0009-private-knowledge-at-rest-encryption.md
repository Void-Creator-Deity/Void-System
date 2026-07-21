# ADR-0009: Private Knowledge Content Encryption at Rest

- Status: Accepted, implemented and migration verified on 2026-07-18
- Date: 2026-07-18

## Context

Personal knowledge sources can contain sensitive notes, identifiers, study material, and user-created context. The historical implementation stored source bytes, SQLite previews, and Chroma document bodies as plaintext. Access control at HTTP boundaries does not protect those copies when a local database, vector directory, or managed source directory is read outside the application.

The unified library has two visibility levels:

- **private**: content belongs to exactly one user and is never eligible for another user's retrieval.
- **official**: administrator-maintained material intentionally available to every signed-in user.

These are access semantics, not two independent knowledge products. The required privacy guarantee applies to the private level. Official material is not treated as user-secret content merely because it shares the same storage implementation.

## Decision

Use application-layer authenticated encryption (Fernet, version `fernet-v1`) for all persisted private *content copies*:

1. managed private source files;
2. private `knowledge_documents.content_preview` values in SQLite; and
3. private Chroma `documents` chunk bodies.

Chunking and embedding occur only in trusted process memory. Chroma receives plaintext embeddings but encrypted document bodies. A scoped, authorized catalog lookup occurs before the application decrypts a retrieved chunk for a response or model context.

One `KnowledgeSourceCipher` is composed per runtime settings snapshot and is injected into source persistence, the private catalog, and the personal Chroma store. Production requires `DOCUMENT_ENCRYPTION_KEY`. Development may use a protected local key file. A historical development key is moved once into the canonical key location; runtime does not retain a fallback reference to the retired location.

Private records track both `encryption_version` (source bytes) and `index_encryption_version` (Chroma document bodies). Startup first encrypts historical SQLite previews and then moves every private source to its encrypted opaque `<document_id>.bin` managed path, updating the source version and database path together. A durable rebuild replaces historical Chroma chunks; it deletes an obsolete plaintext index before queueing a replacement, deliberately preferring temporary unavailability to retaining plaintext at rest. Normal private reads fail closed for a record that has not yet migrated; they never preserve a plaintext runtime fallback.

Official/shared material remains plaintext by default because every signed-in user is its intended reader. It can be encrypted later only as a separate storage-security policy for administrator content; that policy must preserve its shared access semantics and cannot be represented by silently treating official records as private.

## Consequences

- Private file contents and extracted snippets are not readable from the managed source directory, SQLite preview column, or Chroma document body without the runtime key. Historical filenames are migrated to opaque document-id `.bin` paths. Historical filenames are migrated to opaque document-id `.bin` paths.
- Private Chroma metadata omits title and original filename; those values are resolved from the scoped SQLite catalog only after authorization.
- Embedding vectors, document title, original filename, tags, timestamps, ownership metadata, and the SQLite database file itself are **not** encrypted by this decision. Vectors can leak partial semantic information, so this is not a zero-disclosure claim.
- Full SQLite and vector-directory encryption requires a separate decision using SQLCipher or equivalent plus encrypted storage volumes and a managed key-rotation plan. It must not be claimed merely because selected fields use Fernet.
- Key rotation is not implemented. A later version must add a key identifier, dual-read or controlled maintenance window, re-encryption jobs, rollback policy, and verification before retiring an old key.
- Deleting a document must continue to remove both managed source data and scoped vector chunks; encryption does not replace retention or purge behavior.

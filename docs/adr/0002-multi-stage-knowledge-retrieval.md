# ADR-0002: Multi-Stage Knowledge Retrieval

- Status: Accepted
- Date: 2026-07-12

## Context

The original user knowledge flow performed vector similarity search, deduplicated by document, concatenated content, and asked a model to answer. During the first modularization pass, Knowledge Engine retrieved chunks but the Legacy responder invoked the old QA engine, which performed a second retrieval and ignored the selected evidence. This made reranking ineffective and citations difficult to trust.

## Decision

Knowledge Engine uses a staged pipeline:

1. Semantic retrieval from the current Chroma Adapter.
2. Independent lexical retrieval over stored chunks.
3. Reciprocal Rank Fusion so retrieval scores do not need a shared scale.
4. Evidence reranking with lexical fit, deduplication, and per-document diversity.
5. Bounded grounded generation that consumes only the selected evidence.
6. Citation validation against the ranked evidence set.

RRF and the deterministic reranker are default local implementations. Their interfaces remain replaceable by BM25, a cross-encoder, a managed search engine, graph retrieval, or learned ranking without changing callers.

## Consequences

- Retrieval occurs once per answer and its output is the actual model context.
- Keyword-sensitive queries can recover chunks that embedding search may miss.
- Responses expose evidence and retrieval diagnostics through stable contracts.
- Lexical recall currently scans a bounded number of Chroma chunks. This is suitable for personal workspaces but must move to a dedicated lexical index before large multi-tenant scale.
- Confidence is an evidence heuristic, not calibrated probability. A future evaluation dataset must calibrate or replace it.

# Layered Profile Workspace

## Why this changes

The first profile implementation treated user understanding as a flat list of
LLM-generated claims. That made a small amount of aggregate task data look like
a personality judgment, exposed internal identifiers as evidence, and allowed
one weak model response to dominate the screen. A profile is useful only when
the user can see what is established, what is changing, and what is merely an
idea the system wants them to review.

This design replaces the active flat-claim runtime with a layered, owner-scoped
profile workspace. It borrows the staged cognition principle from
`OpenBiliClaw`, but uses Void System's own first-party data rather than any
platform-specific activity vocabulary.

## Product contract

- The profile describes work preferences and the current workspace context. It
does not infer protected traits, diagnoses, emotions, or life circumstances.
- Raw task and review content is never sent to profile inference by default.
The normal input is a small, permissioned set of derived first-party signals.
- A pattern is an observable aggregate, not a conclusion about the user.
- An observation is a recent, time-bounded change and expires when stale.
- A hypothesis is model-assisted, always reviewable, and never used as AI
context until the user confirms or corrects it.
- A facet is an approved durable preference or an explicitly saved fact. It is
the only profile layer eligible for the compact AI context projection.
- Every displayed statement must have user-readable evidence labels and dates;
identifiers, vector IDs, and internal source references are never UI text.

## Layers

1. **Signals** are deterministic records derived from consented workspace data.
They contain source category, safe metrics, time window, freshness, and a
display label. Example: “4 completed reviews in the past 30 days; 3 included
a next action.”
2. **Patterns** are deterministic, explainable interpretations of signals,
such as “often adds a next step during review.” They include a support score,
coverage, and date range. Patterns are not personality labels.
3. **Observations** describe recent changes, for example a focus shift or a
new planning rhythm. They have an expiry date and do not become profile facts
automatically.
4. **Hypotheses** are cautious AI-written explanations based only on the
current patterns and observations. Their language must be Chinese, grounded,
specific, and falsifiable. They require confirmation, correction, or
dismissal.
5. **Facets** are the stable profile the user owns: work rhythm, planning
preference, execution preference, review preference, collaboration style,
learning preference, and current focus. A facet records whether it came
directly from the user or from a confirmed hypothesis.
6. **Context projection** is a compact, inspectable selection of enabled
facets. It is purpose-scoped by the existing Context Compiler and never
injected silently into every model request.

## Data sources and consent

The first rollout can use only the already permissioned sources:

- aggregate Goal / Run / Step lifecycle metrics;
- structured Run reviews and their non-sensitive aggregate fields;
- user-confirmed profile feedback;
- explicitly opted-in long-term memories.

Titles, descriptions, artifact bodies, chat messages, and library document
contents remain excluded unless a later, separately consented source adapter is
added. A source adapter must produce display labels and safe derived signals;
it must not hand raw user text directly to inference.

## Update lifecycle

- Signal collection is deterministic and idempotent. A versioned source key
updates one record instead of accumulating duplicate observations.
- Pattern compilation runs after collection and can run without an LLM.
- Hypothesis generation is an explicit user action in the first rollout. It is
asynchronous-ready but must return a persisted result or a clear failure.
- Confirming or correcting a hypothesis creates or updates a Facet and records
an auditable feedback event. Dismissing it suppresses equivalent suggestions
until new supporting signals arrive.
- Facets are never overwritten by a later model output. Conflicting evidence
becomes a new hypothesis or a recent observation.
- The system keeps a compact changelog of meaningful profile changes.

## API read model

`GET /api/companion/profile` becomes the authoritative workspace payload:

```json
{
  "summary": {"established": 2, "reviewing": 1, "signals": 5, "updated_at": "..."},
  "facets": [],
  "patterns": [],
  "observations": [],
  "hypotheses": [],
  "sources": [],
  "context_projection": {"enabled": true, "facets": []}
}
```

Each item includes a stable public ID, Chinese presentation copy, state,
freshness, and evidence references expressed as public signal IDs. The API may
continue returning the former `raw_claims` and `effective_claims` only during
the one-way database migration; new frontend code must not consume them.

## Migration and deletion policy

Existing observations are converted into Signals with readable source labels.
Existing pending claims are migrated into Hypotheses with `origin=legacy`.
Confirmed and corrected claims become Facets with their original audit metadata.
Rejected claims become suppressions. Once the new read model has tests and the
frontend no longer calls the old suggestion endpoints, the flat claim runtime
and its routes are removed rather than kept as a permanent compatibility path.

## Quality gates

- Deterministic compiler tests cover empty, sparse, conflicting, and stale
histories.
- LLM tests reject English output, generic advice, unsupported claims, missing
evidence, and evidence identifiers outside the supplied signal set.
- HTTP tests prove owner scoping, consent enforcement, migration behaviour, and
that only confirmed facets are emitted to context.
- Browser tests cover empty, learning, review, confirmed, and corrected states
on desktop and mobile; no raw internal IDs may be visible.

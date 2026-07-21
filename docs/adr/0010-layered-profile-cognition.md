# ADR-0010: Layered Profile Cognition

**Status:** Accepted on 2026-07-19

## Decision

Replace the active flat profile-claim runtime with a layered profile model:
Signals, Patterns, Observations, Hypotheses, Facets, and an explicit Context
Projection. Retain old records only as one-way migration input and history.

## Context

The previous claim-only model used an LLM call as both interpretation and
storage. It had low locality: collection, inference, review, context use, and
presentation each had to understand the same unstructured claim fields. It also
made weak aggregate evidence appear as a durable personal conclusion.

## Consequences

- The profile module owns compilation, review state, source labels, and context
  eligibility behind one interface.
- The database gains explicit persisted layer records, so refreshes do not lose
  progress or force the frontend to recreate state.
- Model output has less authority: it creates only reviewable hypotheses.
- New source types can be added as Signal adapters without changing the profile
  workspace or context compiler contract.
- Existing `profile_claims` and `profile_observations` become migration input
  rather than a second live implementation.

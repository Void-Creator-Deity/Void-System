# Evidence-Based Capability Assessment

## Status

Superseded as the replacement for the user-facing `attributes` feature on
July 21, 2026. The user clarified that the desired product is a novel-style
narrative attribute system, not a real-world capability assessment system. See
`2026-07-21-narrative-attribute-system.md` for the active direction.

The evidence-based capability design remains a possible future, separate
professional-development module. It must not overwrite or redefine the
narrative attribute system.

## Problem

The existing attribute model stores a user-owned name, value, maximum, icon,
and description. It is useful as a progress note, but it cannot honestly claim
to assess a person's capability:

- a number has no defined meaning or level boundary;
- no evidence is required to change it;
- a completed task does not necessarily demonstrate the skill named by the
  task;
- no assessment criterion, source, freshness, or reviewer is recorded;
- an LLM would be able to produce a persuasive but unsupported judgment.

The former `attribute_increments` reward path is intentionally not a solution.
Automatic increments made a number change, but did not establish why the work
demonstrated a capability or whether the capability is still current.

## Product Decision

Replace the user-facing concept of a generic "attribute" with a **capability
record**. A capability is a bounded, observable ability such as "Python API
development" or "technical writing with cited sources". The system reports an
assessment only when it can show the capability definition, the evidence, and
the assessment method.

Four concepts remain separate:

| Concept | Example | What it means | May affect a capability level? |
| --- | --- | --- | --- |
| Capability | Python API development | Demonstrated ability against a named rubric | Yes, with evidence |
| Work pattern | Usually completes a weekly review | Recent, aggregate behaviour | No |
| Growth points | 40 points from a completed step | Non-spendable record of acknowledged work | No |
| Profile facet | Prefers concise planning | User-confirmed preference or fact | No |

"Focus", "mood", and other temporary states must not be represented as
capabilities. They belong in an optional work-pattern or check-in feature with
different privacy and expiry rules.

## Assessment Model

Use an evidence-centred structure. Every supported assessment answers three
questions:

1. **Capability model:** What exactly is being claimed? A capability has a
   scope, a versioned rubric, observable criteria, level definitions, and an
   expiry or review interval.
2. **Evidence model:** What observations can support which criterion, how are
   they scored, and what makes them insufficient or contradictory?
3. **Task model:** What user activity or submitted artefact can produce the
   observation? A task is only eligible when its expected evidence is declared
   before completion or explicitly added by the user afterward.

The system must not infer a capability from a task title, completion count,
chat text, or a single model response.

### Capability definition

Each capability definition stores:

```json
{
  "capability_key": "python_api_development",
  "name": "Python API development",
  "scope": "Build and maintain a small authenticated HTTP API.",
  "rubric_version": 1,
  "criteria": [
    {
      "criterion_key": "http_contract",
      "name": "Defines and implements an HTTP contract",
      "level_expectations": {
        "observed": "Can explain an existing route.",
        "demonstrated": "Implements a route with validation and tests.",
        "corroborated": "Maintains a route through a reviewed change."
      },
      "accepted_evidence_types": ["reviewed_artifact", "verified_task_result"]
    }
  ],
  "review_after_days": 180
}
```

Definitions are product content, not model output. The first release should
ship a small curated catalogue and allow a user to create private definitions
from a template. A user-created definition is labelled private and is never
presented as an external credential.

### Evidence record

An evidence record is immutable after capture. It stores a public explanation
and enough provenance to audit the assessment without exposing private raw
content by default:

```json
{
  "evidence_id": "cap_ev_...",
  "owner_id": "...",
  "capability_key": "python_api_development",
  "rubric_version": 1,
  "criterion_key": "http_contract",
  "source_type": "verified_task_result",
  "source_ref": "run_step:...",
  "captured_at": "...",
  "observed_result": "Route contract and automated test result were supplied.",
  "verification": {
    "method": "user_confirmed | deterministic_check | qualified_review | ai_assisted_review",
    "status": "pending | accepted | rejected",
    "reviewer_ref": "..."
  },
  "privacy": "private",
  "content_hash": "optional integrity fingerprint"
}
```

Evidence types for the first release:

- user-confirmed task deliverable with a declared criterion;
- deterministic result, such as a passing project test command whose exact
  command and result are recorded;
- user-uploaded artefact explicitly submitted for assessment;
- qualified human review when the product later has a trusted reviewer role.

Task title, unreviewed chat, and broad activity counts may be displayed as
context but are never sufficient evidence by themselves.

### Assessment state

Avoid a misleading precision score such as "82/100 capability". A capability
uses an interpretable state plus coverage and confidence:

| State | Meaning |
| --- | --- |
| `unassessed` | Definition exists; no accepted evidence. |
| `exploring` | Some learning or practice evidence, below demonstration threshold. |
| `demonstrated` | Enough accepted evidence meets all required criteria for the defined level. |
| `corroborated` | Demonstrated by more than one independent evidence source or review. |
| `needs_review` | Evidence is stale, conflicted, or the rubric changed. |

`confidence` is not a personality score. It is a transparent evidence-quality
summary calculated from criterion coverage, evidence verification method,
independent-source count, recency, and unresolved contradiction. A level must
not be promoted unless every mandatory criterion has accepted evidence. The UI
shows the missing criteria instead of inventing a value.

## AI Boundary

AI can make the system more useful, but it must not be the authority that
creates a capability claim.

Allowed AI work:

- map user-submitted evidence to already-defined rubric criteria;
- extract a concise candidate observation from an opted-in artefact;
- explain why evidence may or may not meet a criterion;
- propose a next assessment task for a missing criterion;
- detect that a previous assessment needs review because evidence is stale.

Disallowed AI work:

- invent a capability definition, rubric, or level threshold at assessment
  time;
- promote a capability with no accepted evidence;
- read private chats, documents, profile data, or task descriptions without
  that source's explicit assessment permission;
- silently modify a confirmed capability assessment;
- convert growth points, task count, or self-description into a skill level.

An AI-assisted review produces `pending` evidence with its model profile,
prompt/template version, rubric version, input scope, and explanation saved in
the audit record. The user confirms, corrects, or rejects it before it affects
the displayed level. Deterministic checks can become accepted automatically
only when the capability definition explicitly permits that check.

## Task Integration

Task completion remains a work-flow event, not an ability verdict.

When creating or publishing a Step, the user may attach an **assessment
intent**:

```json
{
  "capability_key": "python_api_development",
  "criterion_keys": ["http_contract"],
  "expected_evidence": ["verified_task_result"],
  "requires_user_confirmation": true
}
```

On completion, the run records the normal work evidence. It does not change a
capability automatically. The completion review can offer "use this result as
candidate evidence". Only a validated evidence record reaches the assessment
aggregator. This preserves the existing separation between manual completion
and system-assisted completion.

## Data and API Shape

The canonical backend owns the following resources:

- `capability_definitions`: curated or private versioned rubric definitions;
- `user_capabilities`: owner-scoped capability state and current assessment
  projection;
- `capability_evidence`: immutable accepted, pending, rejected, and superseded
  evidence;
- `capability_assessments`: versioned aggregation decisions with coverage,
  confidence factors, reviewer, and explanation;
- `capability_audit_events`: user decisions, rubric migrations, and policy
  changes.

Suggested first-party routes:

- `GET /api/capabilities`
- `POST /api/capabilities`
- `GET /api/capabilities/{capability_id}`
- `PATCH /api/capabilities/{capability_id}`
- `POST /api/capabilities/{capability_id}/evidence`
- `POST /api/capability-evidence/{evidence_id}/decision`
- `POST /api/capabilities/{capability_id}/assessments/refresh`

`/api/attributes` is retired only after a one-way migration maps old user
attributes to `user_capabilities` with state `unassessed` and a migration note.
It must not remain a permanent parallel representation.

## User Experience

The page should be called **Capability Profile** (Chinese: `能力档案`), not
`属性`. It has three practical views:

1. **Overview:** capabilities grouped by current state, with clear coverage
   labels such as "2 of 3 criteria have accepted evidence".
2. **Capability detail:** a readable rubric, current state, latest evidence,
   missing evidence, confidence factors, and a direct correction/review action.
3. **Evidence inbox:** pending AI-assisted or task-derived evidence that the
   user can confirm, edit, reject, or hide.

Do not use a radar chart or an unexplained total score. Those create visual
confidence without assessment validity. Growth points remain a separate
activity record and must never appear as capability evidence.

## Delivery Sequence

### D0: Domain cut-over

- Introduce the new contracts, repository, migration, and API read model.
- Migrate every existing attribute as `unassessed`; preserve its name,
  description, value, and maximum as legacy notes only, not an assessment.
- Remove the old attribute CRUD route and frontend after the new flow passes
  migration and owner-scope tests.

### D1: Manual evidence and rubric-based assessment

- Ship a small curated capability catalogue and private templates.
- Let users create evidence and explicitly confirm it.
- Implement deterministic coverage and recency aggregation, audit history, and
  the capability detail screen.

### D2: Task evidence integration

- Add assessment intent to the canonical Step draft and publication contracts.
- Record candidate evidence from approved task results without changing a
  capability automatically.
- Add background progress and persisted review states using the existing job
  pattern where AI is involved.

### D3: AI-assisted evidence review

- Add opt-in artefact assessment with strict rubric-only structured output.
- Persist model provenance and require user decision for AI-based promotion.
- Evaluate false positives, unsupported criterion mapping, and refusal paths
  before enabling the feature for all users.

### D4: External evidence and portable credentials

- Consider Git, learning platform, or portfolio connectors only after their
  ownership and consent models are designed.
- Consider Open Badges or another credential export only for a completed
  verification and issuer model. A local capability profile is not itself a
  credential.

## Quality Gates

- An assessment cannot reach `demonstrated` when a required criterion is
  missing, rejected, stale, or only supported by task counts.
- Owner scoping applies to definitions, evidence, assessments, artefacts, and
  audit events.
- A user can see and correct every displayed evidence explanation.
- Raw private content is excluded by default and the actual input scope is
  recorded whenever AI runs.
- AI structured output is rejected if it names a criterion outside the supplied
  rubric, has no evidence reference, or contains a level change without an
  allowed assessment policy.
- Migration tests prove that legacy attribute data appears once as an
  `unassessed` capability and that no new runtime writes use the old table.
- Browser tests cover empty, manual evidence, pending AI review, confirmed
  demonstration, rejected evidence, stale evidence, and mobile layouts.

## Sources Considered

- Evidence-Centred Design: capability/student model, evidence model, and task
  model.
- 1EdTech Open Badges and CASE: criteria, supporting evidence, framework
  alignment, and portable credentials are separate concerns.
- ADL xAPI: activity records need an actor, verb, object, result, and context;
  this project may use an xAPI-inspired envelope later without pretending to be
  a full learning record store.
- NIST AI RMF: AI-generated assessment must remain governable, explainable,
  privacy-aware, and subject to human oversight.

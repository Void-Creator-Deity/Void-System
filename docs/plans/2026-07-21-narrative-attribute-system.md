# Narrative Attribute System

## Status

Proposed. This is the active design for the user-facing `attributes` feature.
It replaces the previous attempt to treat attributes as real-world capability
assessment.

## Product Intent

The product is a personal novel-style system panel: a visible record of the
user's chosen character growth, task progress, titles, and milestones. An
attribute is a **narrative progression value**, not a claim that the system has
objectively measured a person's intelligence, health, competence, or worth.

The experience should answer:

- What kind of character am I building right now?
- Which completed actions advanced that character?
- What title, milestone, or story thread did this unlock?
- What can I choose to develop next?

It must not pretend that a model can diagnose, rank, or certify real human
ability from task completion.

## Core Model

Four related concepts have different jobs:

| Concept | Meaning | Example | Source of change |
| --- | --- | --- | --- |
| Attribute | Permanent narrative growth track | `Execution`, `Insight`, `Creation` | Fixed published task reward or explicit user adjustment |
| Status effect | Temporary narrative state | `Deep Focus: +10% task momentum for 7 days` | Explicit rule with an expiry |
| Title / achievement | Named milestone with an unlock condition | `First Reliable Cycle` | Deterministic rule or user-confirmed event |
| Growth points | Non-spendable acknowledgement of completed work | `+20 growth points` | Atomic Step settlement |

Growth points are not attribute values and attributes are not a hidden ability
score. A task can reward both, but each reward type has a separate ledger and
reason.

## Attribute Catalogue

A new account may choose a template and customize it. The first-party default
should feel like a system novel without asserting medical or psychological
facts:

| Attribute | Narrative meaning |
| --- | --- |
| `行动` | Turning intentions into completed actions |
| `洞见` | Collecting, connecting, and reviewing useful information |
| `创造` | Making a work, solution, or expression |
| `秩序` | Building routines, plans, and maintainable systems |
| `共鸣` | Meaningful collaboration and communication |
| `意志` | Returning to a chosen direction after interruption |
| `命运` | A playful story stat driven only by explicit achievements or user choice |

Templates are optional. Users can add private attributes, rename displayed
labels, choose icons, hide a track, or make an attribute visible only to
themselves. The system catalogue cannot silently replace a user's custom
meaning.

## Data Contract

The canonical backend owns the following resources:

- `attribute_definitions`: system-template or user-private definitions,
  display metadata, ordering, and version;
- `user_attributes`: owner-scoped current value, level band, and presentation
  state;
- `attribute_activity`: immutable ledger entries for each change, including
  source, delta, reason, Run/Step reference, and settlement idempotency key;
- `status_effects`: explicit temporary effects with start, expiry, and source;
- `achievements` and `user_achievements`: deterministic milestone rules and
  immutable unlock history;
- `titles` and `user_title_selection`: unlocked narrative labels and the
  active presentation choice.

An attribute activity record is the important boundary:

```json
{
  "activity_id": "attr_act_...",
  "owner_id": "...",
  "attribute_id": "...",
  "delta": 3,
  "source_type": "step_settlement",
  "source_ref": "run_step:...",
  "settlement_key": "...",
  "reason": "Completed the published first draft step.",
  "created_at": "..."
}
```

The current value is a projection of this ledger plus an explicitly audited
base value. It is never a mutable number with no history.

## Task Attribute Evaluation

A task evaluation is an **attribute evaluation for that task**. Completion only
answers "was the action submitted or confirmed?" The attribute evaluation then
answers "which narrative attributes did this work advance, and at which
published tier?"

A canonical Step therefore locks an attribute evaluation policy at publication
time, rather than only locking one unconditional reward:

~~~json
{
  "growth_points": 20,
  "attribute_evaluation": {
    "mode": "self_confirmed | assisted_review",
    "dimensions": [
      {
        "attribute_key": "creation",
        "criteria": ["A usable first draft exists", "The draft follows the agreed scope"],
        "tiers": [
          {"key": "not_met", "delta": 0},
          {"key": "complete", "delta": 3},
          {"key": "refined", "delta": 5}
        ]
      },
      {
        "attribute_key": "action",
        "criteria": ["The published step was completed"],
        "tiers": [
          {"key": "not_met", "delta": 0},
          {"key": "complete", "delta": 2}
        ]
      }
    ]
  }
}
~~~

The policy is chosen or edited by the user while drafting or publishing the
task. A planner may suggest the attribute mapping and criteria, but it cannot
publish them without review. The evaluator never invents a new attribute,
criterion, tier, or reward value after publication.

### Evaluation lifecycle

1. The user completes a task and supplies the declared outcome or evidence.
2. The system evaluates only the published criteria for that task.
3. In self-confirmed mode, the user selects the achieved tier and it is
   recorded as user-confirmed narrative growth.
4. In assisted-review mode, the AI returns a structured per-criterion,
   per-attribute recommendation with an explanation. The user approves,
   corrects, or rejects it according to the existing assisted-completion policy.
5. The approved tiers write attribute ledger entries atomically with the Step
   transition, growth-point settlement, and event history.

A task can be complete while an optional refinement tier is not met. It can also
advance more than one attribute, but each change must name the task, criterion,
tier, and visible reason. Retrying, refreshing, or receiving the same worker
event cannot settle any attribute twice because the settlement key is unique
per Run, Step, attribute, and tier.

Editing a completed Step cannot mutate its historic evaluation. A correction is
a separate audited reversal or adjustment entry. This preserves the novel-system
feedback loop without letting the model arbitrarily assign character growth.

## Level Bands and Presentation

Attributes may have levels for story readability, but the level formula is
product content, not an assessment claim. Example:

| Value range | Story label |
| --- | --- |
| 0-19 | `初启` |
| 20-59 | `积累` |
| 60-119 | `进阶` |
| 120-199 | `精进` |
| 200+ | `领域` |

The screen presents a system-status panel with the active title, selected
attributes, recent changes, current streaks/status effects, and upcoming
achievement conditions. It should show exactly why a value changed. It should
not show fake evidence confidence, a psychological diagnosis, or a radar chart
that implies scientific measurement.

## AI and Companion Boundary

The companion can make the system feel alive without becoming an unaccountable
judge:

- narrate a settled change using its recorded reason;
- suggest an optional task-to-attribute mapping during planning;
- celebrate an achievement already unlocked by a deterministic rule;
- explain current title, status effects, and recent character progression.

It cannot add or remove attributes, modify values, unlock titles, or claim a
real-world ability unless the user explicitly performs the corresponding
audited action. A user can decide whether their narrative status panel is
included in companion context.

## Marketplace Decision

The retired marketplace stays retired for this release. A stat system does not
need a shop to be satisfying. Titles, achievements, status effects, companion
conversation variants, and visual theme unlocks are viable only when each has
a real state transition, ownership rule, and consumption/presentation path.
No spendable balance or placeholder inventory is reintroduced.

## Migration

Existing `attributes` rows migrate one time into `user_attributes`:

- preserve name, icon, description, current value, and maximum as legacy
  narrative data;
- create a migration activity entry explaining that the initial value came from
  the prior system;
- do not fabricate historical per-task attribute activity that the old database
  cannot prove;
- migrate old values as `legacy_import`, not as verified task rewards;
- delete the old table and `/api/attributes` only after the new read/write
  routes, frontend, migration tests, and production migration check pass.

## Delivery Sequence

### N0: Canonical narrative attribute domain

- Define contracts, SQLite migration, ledger, settlement helper, and owner
  scope.
- Migrate old attribute rows.
- Add one small system-template catalogue and custom private attributes.
- Keep growth point settlement unchanged.

### N1: Task reward and history

- Add immutable `attribute_evaluation` policies to canonical Step publication.
- Evaluate and settle approved attribute tiers atomically with Step completion
  and show the per-criterion activity history.
- Add reversal/adjustment actions with clear user-facing reasons.

### N2: Status panel, titles, and achievements

- Replace the current Growth page with a dedicated `系统面板` / `角色成长`
  workspace.
- Add deterministic achievements, title selection, and temporary status effects.
- Make all empty, loading, error, and historical states usable on mobile.

### N3: Companion flavor and optional presentation unlocks

- Add companion narration based only on settled activity.
- Add only fulfilable cosmetic or interaction unlocks, with a separate ADR
  before any future marketplace returns.

## Quality Gates

- Step reward settlement writes growth points, attribute ledger entries, state
  transition, and event history atomically; a failure rolls all of them back.
- Repeating completion or assisted review settles each attribute reward once.
- Every attribute change has a visible reason and source; value edits write an
  audited adjustment entry.
- The frontend has no parallel old `/api/attributes` implementation after
  cut-over.
- Attributes never become profile facts or real-world capability claims by
  default.
- Migration tests cover existing attribute values, legacy reward data, unique
  settlement keys, owner scope, reversals, and an upgraded production-style
  database.
- Browser tests cover template choice, custom attributes, task settlement,
  duplicate completion, title selection, expired status effects, and mobile
  layout.

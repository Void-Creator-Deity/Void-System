# Growth Reward Settlement and Marketplace Retirement Audit

- Status: In progress
- Date: 2026-07-20
- Scope: Make task-completion rewards durable and remove the unfulfilled reward marketplace.

## Observed State

The canonical Task Execution read model already exposes `task_reward_settlements` in a Run review. However, neither manual completion nor a passing system-assisted review writes a settlement. A completed Step therefore has no durable growth record even though the product renders an "settled reward" area.

The marketplace is the inverse problem: it atomically deducts points, creates inventory rows, and stores purchases, but its catalog items have no product capability, scheduling behavior, entitlement check, or consumption path. The frontend has no marketplace workflow. It gives users a spendable balance without a fulfilled benefit.

## Root Cause

Reward planning, execution, and read models were implemented as disconnected layers. Planning emits a reward amount, canonical Step persistence drops it, and transition persistence does not settle it. Marketplace persistence was retained after its product surface disappeared.

## Product Decision

The product keeps a non-spendable **growth-points** ledger: completing a Step may record a predeclared number of points. Points are an auditable record of completed work, not a currency or store balance.

A Step owns its bounded `reward_spec` when a Run is created. A planning model may propose the value before publication, but cannot determine it at completion time. Manual completion and an approved system-assisted review use the same SQLite transaction. That transaction changes the Step state, writes the immutable settlement, records the matching ledger entry, emits execution events, and unlocks dependent Steps. A unique `(user_id, step_id)` constraint is the final idempotency guard.

Failed, skipped, cancelled, rejected, unavailable, and invalid-review paths do not award points. Attribute changes are not automatically inferred from model output in this iteration; users retain explicit control of their growth directions.

The marketplace, inventory, purchase history, and marketplace HTTP routes are retired. Historical point ledger entries are migrated into the canonical growth-point ledger and remain available as growth activity. Historical experience activity is intentionally retired because no remaining product contract consumes it. Existing marketplace inventory and purchases are deleted because they have no durable, consumable product meaning.

## Affected Layers

- Domain contract: canonical Step reward specification and transition invariant
- Planning: explicit conversion of reviewed plan rewards into Step reward specifications
- SQLite: reward persistence in the Step transition transaction; migration of the schema; marketplace table retirement
- HTTP and composition: marketplace router, schema, dependency, module, adapter, and tests removed
- Personal context: keep completion-point summaries, remove inventory references
- Frontend: use growth-point language and render only settled execution facts
- Analytics: expose recorded growth-point activity, distributions, and health metrics without spend or balance semantics

## Canonical Path

`Goal -> published Run/Step reward_spec -> manual completion OR approved system review -> atomic Step transition + settlement + growth ledger + events -> Run review / Growth activity`

There is no alternate settlement endpoint, compatibility route, client-side balance update, or model-decided reward path.

## Migration and Deletion Strategy

Migration 36 adds `task_steps.reward_spec` when needed, then removes `user_resources` and `purchase_history`. Migration 37 renames the historical `coins` ledger to `growth_point_ledger` and rebuilds settlements with the single `growth_points` value. Migration 38 removes the obsolete `users.experience` column. New databases never create the retired marketplace tables, coin ledger, experience ledger, or experience counter. Marketplace module files, HTTP schemas/routes, dependency wiring, test fixtures, and analytics queries are removed in the same change.

No production runtime reads or writes the retired tables or columns after migration 38. The immutable migration-3 history entry remains only to validate already-created database histories; it performs no runtime role after migration 38.

## Acceptance Criteria

1. A manually completed rewarded Step creates exactly one settlement and one positive growth-ledger entry.
2. A passing assisted review creates the same records; rejected or unavailable reviews create none.
3. Retrying a completion request cannot create duplicate points.
4. Any failure while appending settlement data rolls back the Step completion.
5. Upgrading a database removes marketplace tables and application startup has no marketplace router or dependency.
6. Run review, Growth UI, personal-context access, analytics, tests, OpenAPI, and the frontend build agree on the replacement contract.

## Verification Plan

- SQLite migration tests including an upgraded database with retired marketplace tables
- Task execution unit and HTTP tests for manual, assisted, retry, non-award, and rollback behavior
- Architecture test proving the marketplace router is absent
- Full backend unit suite
- Frontend unit suite and production build
- `git diff --check`

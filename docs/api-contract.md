# API Contract

Status: ACTIVE

This document is the frontend-facing contract for the modular backend. The
OpenAPI document at `/api/openapi.json` is the source of truth for field-level
schema details. Page components should consume the API modules in
`void-system-frontend/src/api/`, never construct ad hoc HTTP calls.

## Transport

- Base path: `/api`
- Authentication: `Authorization: Bearer <access-token>`
- Success envelope: `{ success: true, message, data, request_id }`
- Error envelope: `{ success: false, message, error_code, details, request_id }`
- Access tokens are short lived. On an authentication error, use the refresh
  workflow exposed by the existing authentication client, then retry once.
- Administrator routes require an administrator session. Do not show their
  controls to ordinary members.

## Stable Product Areas

| Area | Frontend module | Primary endpoints |
| --- | --- | --- |
| Authentication and account | `user.js` | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/user/password` |
| Goals and execution | `goals.js`, `runs.js` | `/goals`, `/goals/{goal_id}/runs`, `/runs/*`, `/approvals/*` |
| Planning | `plans.js` | `/plans` |
| Automation and steering | `triggers.js`, Run methods in `runs.js` | `/triggers/*`, `/runs/{run_id}/commands/*` |
| System companion and personal context | `companion.js` | `/companion/settings`, `/companion/briefing`, `/companion/context`, `/companion/profile/*`, `/companion/memories/*` |
| Legacy task compatibility | no first-party page client | `/task-categories`, `/task-chains`, `/tasks`, `/ai/advisor` |
| Growth profile and points | `growthProfile.js` | `/attributes`, `/coins/balance`, `/coins/history`, `/coins/stats` |
| Conversations | `chat.js`, `session.js` | `/chat/groups`, `/chat/sessions`, `/chat/messages` |
| Personal knowledge | `document.js`, `rag.js` | `/user/documents`, `/user/qa/ask`, `/knowledge/search` |
| Shared system knowledge | `knowledge.js` | `/knowledge/system/search`, `/knowledge/system/ask` |
| Admin configuration | `administration.js`, `knowledgeAdministration.js` | `/admin/system/*`, `/admin/rag/*` |

## Knowledge Workflows

### Personal knowledge

- Upload: `POST /user/documents/upload` as multipart form data. Send one or more
  `files`, optional `title`, and optional `tags`.
- List: `GET /user/documents?retention=active|archived|all`. The default is
  `active`. Each document includes `is_archived` and can include an `ingestion`
  record with queued, processing, completed, or failed preparation state.
- Archive: `DELETE /user/documents/{document_id}`. This moves the source to
  retention, hides it from every retrieval path, and remains reversible.
- Restore: `POST /user/documents/{document_id}/restore`. Archived source and
  existing indexed content become available again.
- Permanent removal: `DELETE /user/documents/{document_id}/purge`. This only
  accepts archived documents. If index cleanup is unavailable, the source stays
  archived so the user can retry safely.
- Rebuild: `POST /user/documents/rebuild-index`. Treat the response as an
  accepted background operation and refresh document status rather than waiting
  on the request.
- Search: `POST /knowledge/search` with `{ query, top_k }`.
- Answer: `POST /user/qa/ask` with `{ question, document_ids? }`.
  Render `sources` and `support` alongside the answer. `confidence` remains a
  compatibility field and should not be presented as a user-facing percentage.
  `support.status` is `ready` when the answer is sufficiently supported, or
  `needs_more_context` when the user should add material or refine the question.

### Shared system knowledge

Shared knowledge is curated by administrators but available to signed-in users.
It uses the same hybrid retrieval and evidence model as personal knowledge.

- Search: `POST /knowledge/system/search` with
  `{ query, top_k?, tags? }`.
- Answer: `POST /knowledge/system/ask` with `{ question, tags? }`.
  It returns the same `support` object as personal knowledge answers.
- Results always include `scope: "system"`; cite the returned title, file name,
  and tags instead of exposing vector or provider internals.

### Retired knowledge routes

Do not call `/api/lc/qa` or use `type: "qa"` with `/api/stream-chat`.
They are intentionally retired and return a migration response. Use
`/api/user/qa/ask` or the shared system knowledge routes above.

## System Companion and Personal Context

The companion is a permissioned context gateway. It reads only the user-approved
sections requested by the client and returns provenance, selection reasons, and
access records; it is not a hidden channel for unrestricted profile or document
access.

- Settings: use `GET` and `PUT /companion/settings`. The `permissions` object
  is the source of truth for what may enter a briefing or context snapshot. Keep
  profile analysis opt-in; do not enable it on behalf of a user.
- Briefing and context: use `GET /companion/briefing` for the primary companion
  surface and `GET /companion/context` when a page needs a bounded, explicitly
  requested section set. Render the returned explanations instead of exposing
  internal ranking details.
- Profile: use `GET /companion/profile` and `GET /companion/profile/suggestions`.
  Suggestions are reviewable first-party patterns, not facts. The UI must offer
  confirm, correct, or reject actions through the matching review endpoint and
  must never silently promote a suggestion.
- Memory: use `GET` and `POST /companion/memories` for user-authored memory.
  System-created candidates are available from `GET /companion/memories/suggestions`
  and must be confirmed, corrected, or rejected through
  `PATCH /companion/memories/{memory_id}/review` before use in context.
  `DELETE /companion/memories/{memory_id}` archives; permanent removal is the
  separate `DELETE /companion/memories/{memory_id}/purge` operation and only
  applies after archival.
- Expiry: an expired active memory remains visible to its owner but is excluded
  from context. Updating `expires_at` through `PATCH /companion/memories/{memory_id}`
  may make it context-eligible again when it is otherwise active and confirmed.
- Access history: `GET /companion/access-log` is for transparent explanation of
  companion data use. Do not infer user preferences from raw log text in the UI.

## Goal and Run Execution

Task Execution is the canonical contract for new work. A simple personal task is a
Goal with a one-Step Run. Assisted and agent work use the same contract and differ
only by `run.mode`.

- Create a Goal: `POST /goals`.
- Edit, complete, archive, or reopen a Goal with `PATCH /goals/{goal_id}`. Archived Goals cannot create new Runs until reopened.
- Create a Run: `POST /goals/{goal_id}/runs` with `mode` and one or more Steps.
- Step dependencies refer to stable request-local `client_key` values. Omit
  dependencies for root or parallel Steps.
- Start, pause, resume, and cancel using command endpoints on `/runs/{run_id}`.
- Start, complete, fail, retry, or explicitly skip a Step through its Run command endpoints. Skipping is auditable and can release dependent Steps.
- Start, complete, fail, and retry Steps using command endpoints below the Run.
- A Step with `requires_approval: true` enters `waiting_approval` before its
  first attempt. Resolve the durable Approval through `/approvals/{approval_id}/resolve`.
- Record agent and tool operations as Actions. Return reviewable outputs as
  Artifacts, not implementation logs embedded in status messages.
- Read `/runs/{run_id}/events` for the append-only execution timeline.
- Claim agent work with `POST /runs/{run_id}/lease` and `{ worker_id, lease_seconds }`. The response returns the secret `lease_token` once to the worker.
- Renew ownership and persist resumable state with `POST /runs/{run_id}/heartbeat` and `{ lease_token, lease_seconds, checkpoint_data? }`.
- Release ownership with `POST /runs/{run_id}/lease/release` and `{ lease_token, checkpoint_data? }`. Expired leases may be reclaimed by another worker; stale tokens are rejected.
- Run detail responses expose lease owner, expiry, and checkpoint state but never expose the lease token.
- Clients must treat command responses as authoritative Run snapshots.

Legacy `/tasks` and `/task-chains` remain compatibility paths during migration. Their writes are atomically projected into the same Goal, Run, Step, Event, and Approval records, and migration 10 backfills existing data. Do not add new product behavior to those contracts.

## Automation and Run Steering

Task Automation adds entry conditions and user steering to canonical Runs. It does not create another task architecture.

- Create a Trigger: `POST /triggers` with `goal_id`, `name`, `trigger_type`, `configuration`, and a validated `run_template`. Supported types are `schedule` and `event`.
- List and inspect Triggers with `GET /triggers` and `GET /triggers/{trigger_id}`.
- Edit a Trigger name, configuration, or validated Run template with `PATCH /triggers/{trigger_id}`; delete a no-longer-needed Trigger with `DELETE /triggers/{trigger_id}`. Existing Runs remain durable.
- Pause or resume creation of new Runs with `POST /triggers/{trigger_id}/pause` and `POST /triggers/{trigger_id}/resume`. Replaying a previously recorded source key remains idempotent even after a Trigger is paused.
- Fire through `POST /triggers/{trigger_id}/fire` with a stable `source_key` and optional `payload`. The same Trigger and source key always resolve to the same Run. Scheduler and integration Adapters must retry with the same source key after uncertain delivery.
- Schedule configuration accepts either `cron` or `interval_seconds`; user-facing screens should provide a friendly schedule builder and translate it in the domain client rather than expose raw cron as the primary control. Event configuration requires `event_type`.
- Submit steering input with `POST /runs/{run_id}/commands`. Supported command types are `instruction` and `follow_up`; provide an `idempotency_key` when a client may retry. Terminal Runs reject new commands.
- Workers read commands with `GET /runs/{run_id}/commands?status=pending` and acknowledge incorporation with `POST /runs/{run_id}/commands/{command_id}/acknowledge`. Acknowledgement is idempotent.
- Trigger firing, command submission, and command acknowledgement emit append-only Events. Clients should use Run detail and Event responses as authoritative state.

## AI and Streaming

- Conversation streaming: `POST /stream-chat` with `type: "persona"`. This is an SSE response; consume `message`, `done`, and `error` events.
- Canonical planning: `POST /plans` with `{ topic, execution_mode, max_steps }`. It returns a reviewable `{ goal, run, summary, estimated_duration, meta }` specification only; this request never creates a Goal, Run, legacy task, or task chain. Publish the user-reviewed draft through the Goal and Run endpoints.
- Legacy planning: `POST /ai/advisor` with `{ topic, force_mode }` remains compatible and returns `{ mode, query, response, estimated_duration, tasks, meta }`. The first-party frontend no longer branches its architecture on `single_task` or `workflow_chain`; do not reintroduce that split.
- Task progress: `PUT /tasks/{task_id}/progress` with `{ progress: 0..100 }`. Progress tasks complete automatically at 100%.
- AI-evaluated task completion: `POST /tasks/{task_id}/ai-evaluate` with submitted evidence. Never call the generic status endpoint to complete one.
- Proof-based task completion: `POST /tasks/{task_id}/proof` with evidence, then `PUT /tasks/{task_id}/status?status=completed`. The status update verifies that proof exists before settling the task.
- Image captions: `POST /ai/image-caption` using the uploaded session file ID.
- The administrative connection screen uses `GET`, `PUT`, and
  `POST /admin/system/ai-config[/test]`. It is not a general user preference
  surface.

## Frontend Rules

1. Keep API calls inside domain clients. Pages and composables should call named
   client methods rather than `axios.post('/api/...')` directly.
2. Treat every write response as authoritative; refresh the affected read model
   rather than locally guessing database state.
3. Show user language from `message` and use `error_code` for branching.
   Do not surface stack traces, vector IDs, provider credentials, or raw errors.
4. Model settings are an administrator-only connection concern. Never persist
   provider credentials in browser storage.
5. Knowledge ingestion and task generation are asynchronous. Their UI needs
   clear pending, completed, failed, and retry states.

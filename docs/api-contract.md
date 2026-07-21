# API Contract

Status: ACTIVE

Last updated: 2026-07-18

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
| Planning | `plans.js` | `/plan-generations`, `/plan-generations/{generation_id}`, `/plan-drafts/*` |
| Automation | `triggers.js` | `/triggers/*` |
| System companion and personal context | `companion.js` | `/companion/settings`, `/companion/briefing`, `/companion/context`, `/companion/profile/*`, `/companion/memories/*` |
| Growth profile and points | `growthProfile.js` | `/attributes`, `/growth/points/balance`, `/growth/points/activity`, `/growth/points/summary` |
| Conversations | `chat.js`, `session.js` | `/chat/groups`, `/chat/sessions`, `/chat/messages` |
| Personal knowledge | `document.js`, `rag.js` | `/user/documents`, `/user/qa/ask`, `/knowledge/search` |
| Shared system knowledge | `knowledge.js` | `/knowledge/system/search`, `/knowledge/system/ask` |
| Admin configuration | `administration.js`, `knowledgeAdministration.js` | `/admin/system/*`, `/admin/rag/*` |

## Knowledge Workflows

### Personal knowledge

Personal knowledge ingestion is durable server-owned work. Upload and rebuild
requests only persist a source version and a task; parsing, optional image
understanding, vector replacement, and final document status changes run in the
application worker. Browser state is never the authority and must be recoverable
from the task endpoints after refresh or reconnect.

- Upload: \`POST /user/documents/upload\` as multipart form data. Send one or more
  \`files\`, optional \`title\`, and optional \`tags\`. Each successful result contains
  \`doc_id\`, \`job_id\`, and an \`ingestion\` task snapshot with \`status: queued\`.
  It does not mean that the source is already searchable.
- List: \`GET /user/documents?retention=active|archived|all\`. The default is
  \`active\`. Each document includes \`is_archived\` and its latest \`knowledge_status\`
  when available.
- Rebuild: \`POST /user/documents/rebuild-index\`. It returns \`jobs\`, \`queued_count\`,
  \`failed_count\`, and source-file validation failures. It never waits for parsing or
  indexing in the request.
- Task history: \`GET /user/knowledge/jobs?limit=30\` and
  \`GET /user/knowledge/jobs/{job_id}\`. Render \`status\`, \`stage\`, \`progress\`,
  \`error_message\`, \`document_title\`, \`document_name\`, and \`result\` from these
  server snapshots. Tasks transition through \`queued -> processing -> completed | failed |
  cancelled\`; a cancellation request for active work can temporarily be \`cancelling\`.
- Task controls: \`POST /user/knowledge/jobs/{job_id}/cancel\` cancels queued work
  immediately or requests cooperative cancellation for active work.
  \`POST /user/knowledge/jobs/{job_id}/retry\` creates a fresh \`queued\` task from the
  immutable source version only after a task is \`completed\`, \`failed\`, or \`cancelled\`.
  Active work returns \`409 KNOWLEDGE_JOB_NOT_RETRYABLE\` instead of falsely reporting a retry.
- Task security: all task reads and writes are owner-scoped. Worker lease fields,
  provider details, vector identifiers, and source bytes are never public response fields.
- Archive: \`DELETE /user/documents/{document_id}\`. This moves the source to
  retention, hides it from every retrieval path, and remains reversible.
- Restore: \`POST /user/documents/{document_id}/restore\`. Archived source and
  existing indexed content become available again.
- Permanent removal: \`DELETE /user/documents/{document_id}/purge\`. This only
  accepts archived documents. If index cleanup is unavailable, the source stays
  archived so the user can retry safely.
- Search: \`POST /knowledge/search\` with \`{ query, top_k }\`.
- Answer: \`POST /user/qa/ask\` with \`{ question, document_ids? }\`.
  Render \`sources\` and \`support\` alongside the answer. \`confidence\` remains a
  compatibility field and should not be presented as a user-facing percentage.
  \`support.status\` is \`ready\` when the answer is sufficiently supported, or
  \`needs_more_context\` when the user should add material or refine the question.

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
  is the source of truth for what may enter a briefing or context snapshot. `tone`,
  `initiative`, and the bounded `persona` object are an interaction policy passed
  to first-party AI calls; persona text cannot grant data access or override core
  instructions. Keep profile analysis opt-in; do not enable it on behalf of a user.
- Briefing and context: use `GET /companion/briefing` for the primary companion
  surface and `GET /companion/context` when a page needs a bounded, explicitly
  requested section set. Render the returned explanations instead of exposing
  internal ranking details.
- Profile: use `GET /companion/profile`, `GET /companion/profile/suggestions`, and
  `POST /companion/profile/infer`. Inference is opt-in through the `profile`
  permission. Before requesting the model, the server may refresh only conservative,
  first-party task-history aggregates (goals, runs, steps, reviews, recovery, and
  plan-refinement counts) into traceable observations. It never harvests chat text,
  artifact/document bodies, raw review notes, or external-platform activity.
  Suggestions are reviewable patterns, not facts. The UI must offer confirm, correct,
  or reject actions and must never silently promote a suggestion.
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
Goal with a one-Step Run. The product exposes two completion paths: `manual`
(user-facing: 自己完成) and `assisted` (user-facing: 系统协助).

- Create a Goal: `POST /goals`.
- Edit, complete, archive, or reopen a Goal with `PATCH /goals/{goal_id}`. Archived Goals cannot create new Runs until reopened.
- Create a Run: `POST /goals/{goal_id}/runs` with `mode` and one or more Steps. Only `manual` and `assisted` are accepted.
- Step dependencies refer to stable request-local `client_key` values. Omit dependencies for root or parallel Steps.
- Start, pause, resume, retry, and cancel through their explicit Run state-transition endpoints.
- Start, complete, fail, retry, or explicitly skip a Step through its explicit Step state-transition endpoints. Skipping is auditable and can release dependent Steps.
- A Step with `requires_approval: true` enters `waiting_approval` before its first attempt. Resolve the durable Approval through `/approvals/{approval_id}/resolve`.
- For a manual Run, submit output and optional Artifacts through `POST /runs/{run_id}/steps/{step_id}/complete`; the user’s command completes the running Step.
- For an assisted Run, submit output and optional Artifacts through `POST /runs/{run_id}/steps/{step_id}/review`. The response includes a durable `review` result. Only `passed` completes the Step. `revision_requested` and `unavailable` preserve the running Step and evidence so the user can improve or retry.
- Record auditable operations as Actions. Return reviewable outputs as Artifacts, not implementation logs embedded in status messages.
- Read `/runs/{run_id}/events` for the append-only execution timeline. Clients must treat state-transition responses as authoritative Run snapshots, including step review records.

The retired `agent` Run mode and worker-lease routes do not exist. Historical agent data is migrated once to assisted work. The retired `/tasks`, `/task-chains`, task-category, and automatic-task runtime contracts no longer exist. Historical records are converted once by ordered migrations. First-party or integration callers must not probe or fall back to those routes.

## Automation Triggers

Task Automation adds entry conditions to canonical Runs. It does not create another task architecture or a hidden instruction queue.

- Create a Trigger: `POST /triggers` with `goal_id`, `name`, `trigger_type`, `configuration`, and a validated `run_template`. Supported types are `schedule` and `event`.
- List and inspect Triggers with `GET /triggers` and `GET /triggers/{trigger_id}`.
- Edit a Trigger name, configuration, or validated Run template with `PATCH /triggers/{trigger_id}`; delete a no-longer-needed Trigger with `DELETE /triggers/{trigger_id}`. Existing Runs remain durable.
- Pause or resume creation of new Runs with `POST /triggers/{trigger_id}/pause` and `POST /triggers/{trigger_id}/resume`. Replaying a previously recorded source key remains idempotent even after a Trigger is paused.
- Fire through `POST /triggers/{trigger_id}/fire` with a stable `source_key` and optional `payload`. The same Trigger and source key always resolve to the same Run. Scheduler and integration Adapters must retry with the same source key after uncertain delivery.
- Schedule configuration accepts either `cron` or `interval_seconds`; user-facing screens should provide a friendly schedule builder and translate it in the domain client rather than expose raw cron as the primary control. Event configuration requires `event_type`.
- Trigger firing emits append-only Events. Clients should use Run detail and Event responses as authoritative state. To change direction, finish, cancel, or review the existing Run and create a follow-up Run.

## AI and Streaming

- Conversation streaming: `POST /stream-chat` with `type: "persona"`. This is an SSE response; consume `message`, `done`, and `error` events.
- Durable planning: `POST /plan-generations` with `{ topic, execution_mode, max_steps, advisor_prefs? }` returns `202` and a persistent generation snapshot. `GET /plan-generations` restores recent owner-scoped jobs after refresh; `GET /plan-generations/{generation_id}` reads one job; `DELETE /plan-generations/{generation_id}` requests cancellation. The application-owned background Job worker atomically leases plan-generation jobs from SQLite, records progress, cooperatively honours cancellation, and requeues interrupted work after a restart. This lease is internal Job coordination, not a user Run execution mechanism. A ready job always exposes `draft_id`; the browser must load that draft instead of treating the job result as durable plan state. Lease tokens are never returned through HTTP.
- Plan Drafts: `GET /plan-drafts` returns recent owner-scoped review records; `GET /plan-drafts/{draft_id}` returns the authoritative editable payload, `version`, `status`, and any published Goal/Run identifiers. `PATCH /plan-drafts/{draft_id}` accepts `{ payload, expected_version }` and increments the optimistic version. On `PLAN_DRAFT_VERSION_CONFLICT`, reload the draft; do not overwrite with stale browser data. `POST /plan-drafts/{draft_id}/publish` accepts `{ idempotency_key }` and atomically creates Goal, Run, Steps, dependencies, and initial events. Reuse the same key only for retrying the same uncertain publish request. Its published response contains `published_goal_id` and `published_run_id`.
- A Plan Draft starts as `ready`, becomes `published` exactly once, and may not be edited after publication. The first-party UI must use these endpoints for history, edits, refresh recovery, and publication. It must not store durable plans in localStorage/sessionStorage or chain Goal create, Run create, and Run start requests.
- Retired synchronous planning routes: `POST /plans` and `POST /ai/advisor` are intentionally absent. Integrations must use durable Plan Generation and Plan Draft endpoints; they must never probe or fall back to retired routes.
- Image captions: `POST /ai/image-caption` using the uploaded session file ID.
- The administrative connection screen uses `GET` and `PUT /admin/system/ai-config`, `POST /admin/system/ai-config/models` for upstream discovery, and `POST /admin/system/ai-config/test` for capability-aware verification. Discovery, verification, and runtime calls must resolve the same normalized connection profile. For a custom endpoint configured through `LLM_PROVIDER=openai`, the runtime explicitly aggregates streamed chat-completion text so GPT-like model names cannot silently switch the gateway to an incompatible protocol. It is not a general user preference surface.

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


## AI Runtime Configuration Contract

The administrator-only endpoints below operate on the canonical AI connection
profile. Secrets are never returned.

- GET /api/admin/system/ai-config returns the persisted editable profile,
  supported providers, upstream model options when discoverable, and masked
  environment entries.
- POST /api/admin/system/ai-config/models accepts unsaved form values and
  returns model_options plus runtime_profile. runtime_profile is credential-safe
  and includes provider, protocol, normalized base_url, model, locality, and
  request options.
- POST /api/admin/system/ai-config/test uses the exact same runtime_profile to
  discover the model and verify one visible chat response. A successful result
  is evidence for the corresponding runtime client, not merely TCP reachability.
- PUT /api/admin/system/ai-config persists an explicit profile and atomically
  publishes a new runtime settings snapshot when apply_runtime is true. New
  requests use it immediately; existing requests keep their captured snapshot.

Errors use stable codes including AI_PROVIDER_NOT_SUPPORTED,
AI_CREDENTIAL_REQUIRED, AI_ENDPOINT_REQUIRED, AI_MODEL_REQUIRED,
AI_MODEL_NOT_FOUND, AI_MODEL_DISCOVERY_FAILED, and AI_CHAT_TEST_FAILED.

## Runtime AI Transport Errors

POST /api/stream-chat creates its persona chain from the request's captured
runtime settings. Each SSE error event has finished: true, a safe message, and
a stable error_code. Configuration errors retain their canonical code, such as
AI_PROVIDER_NOT_SUPPORTED, AI_MODEL_REQUIRED, AI_CREDENTIAL_REQUIRED, or
AI_ENDPOINT_REQUIRED. Provider or network failures use AI_UPSTREAM_UNAVAILABLE.

POST /api/ai/image-caption uses the same captured settings and returns the
standard API error envelope with the same stable AI codes. Neither endpoint
returns model credentials, internal prompts, or raw upstream error bodies.


### Task Evidence Evaluation Result

Where task-evidence evaluation is exposed, its result is normalized before it
leaves the service boundary: `status` is `pass` or `fail`, `score` is an
integer from 0 to 100, and `feedback` is non-empty. The evaluator never selects
or returns rewards: the published Step owns its bounded `reward_spec`, and only
a confirmed completion can settle those predeclared growth points. Malformed
upstream model output is represented as a safe `fail` result.

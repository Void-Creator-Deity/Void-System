# Void System Backend

The FastAPI backend for the Void System personal growth workspace. New execution behavior is built around Goal → Run → Step and portable Core interfaces; legacy task and RAG implementations remain behind compatibility adapters during their deprecation window.

## Canonical modules

- **Task Execution** owns Goal, Run, Step, Action, Event, Artifact, Approval, Worker Lease, Checkpoint, Run Command, and atomic Reward Settlement rules.
- **Task Automation** owns Trigger lifecycle and idempotent Trigger Firing, then delegates execution state to Task Execution.
- **Planning Engine** creates reviewable Goal and Run specifications without coupling callers to advisor-chain output modes.
- **Knowledge Engine** owns ingestion, retrieval, answer support, citations, traces, evaluation, and index lifecycle behind portable interfaces.
- **Identity, Conversations, Growth, Analytics, and Administration** expose focused domain operations through HTTP adapters.

Legacy `/api/tasks`, `/api/task-chains`, task categories, reward paths, and optional LangServe routes are compatibility surfaces. New product behavior belongs to the canonical modules, and legacy writes are projected into the same execution records.

## API contract

- JSON authentication: `POST /api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, and `/api/auth/logout`
- Goals and execution: `/api/goals`, `/api/runs`, `/api/approvals`
- Planning: `/api/plans`
- Automation and steering: `/api/triggers`, `/api/runs/{run_id}/commands`
- Personal and shared knowledge: `/api/user/documents`, `/api/user/qa`, `/api/knowledge`
- Administration: `/api/admin/system`, `/api/admin/rag`
- OpenAPI UI: `/api/docs`; schema: `/api/openapi.json`

Every error uses the same envelope with `success=false`, a stable `error_code`, safe optional `details`, and a request ID. Access and refresh tokens are distinct; refresh tokens rotate and are stored only as hashes.

## Local development

```powershell
cd void-system-backend
copy .env.example .env
uv sync
uv run main.py
```

The default server is `http://127.0.0.1:8000`, with API docs at `http://127.0.0.1:8000/api/docs`.

## Configuration

Set a unique `SECRET_KEY` of at least 32 characters in production. Configure explicit `CORS_ORIGINS`, persistent `DATABASE_URL`, file and Chroma locations, and the selected chat and embedding providers. `BOOTSTRAP_ADMIN_ENABLED`, `ENABLE_TEST_USER_ENDPOINT`, and `ENABLE_LANGSERVE_ROUTES` are opt-in.

The application owns one RuntimeSettings instance and one Database adapter per FastAPI app. Routes receive focused interfaces from dependency composition instead of constructing storage or model resources directly.

## Local administrator recovery

If the local administrator password is lost, reset the existing SQLite administrator without enabling bootstrap or storing a password in the repository:

```powershell
$env:VOID_ADMIN_PASSWORD = 'use-a-temporary-strong-password'
uv run python tools/reset_local_admin.py --username admin --email admin@void-system.com
Remove-Item Env:VOID_ADMIN_PASSWORD
```

The tool refuses to create or promote an account. It only repairs an existing administrator, increments the account token version, and revokes all previous login sessions. Omit `VOID_ADMIN_PASSWORD` to enter and confirm the password interactively. Use `--database` when recovering a non-default database.

## Verification

```powershell
uv run python -m unittest discover -s tests -v

# Current Windows workspace fallback when uv is not on PATH
& '.\.venv313\Scripts\python.exe' -m unittest discover -s tests -v
```

Use only an environment synchronized from pyproject.toml and uv.lock. An unrelated global Python may import part of the suite while missing FastAPI and other runtime dependencies.

The suite covers SQLite migrations, identity and token rotation, Goal/Run/Step transitions, worker leases and checkpoints, triggers and commands, legacy projections, reward idempotency, conversations, knowledge lifecycle, planning, administration, and HTTP owner isolation.

For the explicit local LM Studio smoke test only:

```powershell
$env:RUN_LMSTUDIO_INTEGRATION = "1"
uv run python tools/test_lmstudio_gemma.py
```

The probe expects `google/gemma-4-12b-qat` at `http://127.0.0.1:1234/v1` and does not change normal application configuration.

## Production notes

- Run behind a TLS-terminating reverse proxy with explicit browser origins.
- Persist and back up SQLite, user files, session attachments, and the vector index.
- Keep bootstrap/test routes disabled after provisioning.
- Use one shared durable database and storage location per deployment; avoid starting multiple development backends against the same Chroma directory.
- Run migrations and the full test suite before replacing an existing deployment.

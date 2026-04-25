# VerifyFlow

VerifyFlow is an agent execution and verification platform for turning a user goal into planned tasks, running those tasks through tool-backed executors and recording whether the work actually satisfied the requested outcome. It combines a FastAPI backend, a Next.js dashboard, deterministic verifiers, optional LLM judge fallback, a durable run worker, telemetry, audit-style ledgers, review escalation and benchmark workflows.

## Problem

LLM agents can produce convincing progress while leaving the real outcome ambiguous. VerifyFlow is built around the opposite assumption: execution should be observable, recoverable and independently checked. A run is planned, executed, verified and logged. When the system cannot support or verify the goal, the run is escalated for manual review instead of being marked as successful by default.

## Core Features

- **Agent execution:** planner, executor, verifier and judge components coordinate run tasks through the backend orchestration graph.
- **Deterministic verification:** filesystem, browser and GitHub verifier modules can check concrete evidence instead of relying only on model output.
- **Judge fallback:** an LLM judge can assess evidence when deterministic checks are insufficient or unavailable.
- **Telemetry and ledger:** task attempts, verification confidence, latency, token usage, tool calls and ledger entries are persisted for auditability.
- **Review queue:** escalated tasks can be reviewed, approved, rejected or sent back for another queued run.
- **Benchmarks:** benchmark suites and cases exercise runs against known scenarios and expected outcomes.
- **Frontend dashboard:** the Next.js UI exposes runs, run details, task state, telemetry, ledgers, review queues, configurations and benchmarks.
- **Durable execution:** runs are persisted as queued work and processed by a worker with claim leases, failure recording and stuck-run recovery helpers.

## Architecture

```text
Next.js frontend
    |
    | authenticated API calls and run streaming
    v
FastAPI backend
    |
    | SQLAlchemy models / Alembic migrations
    v
PostgreSQL or SQLite-compatible development database
```

The backend exposes authenticated API routes under `/api`, stores domain state with SQLAlchemy and manages database shape through Alembic. New runs are inserted as `queued`; a separate worker claims queued runs, executes the orchestration graph, records failures and clears its lease when finished.

At a high level, the run flow is:

```text
user goal -> planner -> task list -> executor -> verifier -> judge fallback -> completed / failed / needs_review
```

Unsupported goals, planner failures, unverifiable work and failed verification paths can end in `needs_review` rather than being disguised as completed work.

## Repository Layout

```text
backend/     FastAPI API, SQLAlchemy models, Alembic migrations, agents, worker and tests
frontend/    Next.js app, typed API client, dashboard components, auth integration
.github/     Backend, frontend and dependency security workflows
```

## Local Setup

### Prerequisites

- Python 3.12
- Node.js 20
- npm
- PostgreSQL 16 for the default local database or another database URL supported by SQLAlchemy/Alembic

The included `docker-compose.yml` defines a PostgreSQL service. Use only the database service for local development unless you add complete Dockerfiles for the apps:

```bash
docker compose up -d postgres
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Edit `backend/.env` and set real values. The required backend variables are:

- `DATABASE_URL`
- `NEXTAUTH_SECRET`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_JUDGE_MODEL`
- `MAX_RETRIES`
- `VERIFICATION_CONFIDENCE_THRESHOLD`

Optional backend variables include:

- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `FILESYSTEM_ALLOWED_PATHS`
- `BROWSER_CHANNELS`

Run migrations:

```bash
cd backend
alembic upgrade head
```

Start the API:

```bash
cd backend
uvicorn app.main:app --reload
```

Start the durable run worker in a separate terminal:

```bash
cd backend
python -m app.worker.run_worker
```

If you use browser tools locally, you may also need to install Playwright browsers:

```bash
cd backend
python -m playwright install
```

### Frontend

```bash
cd frontend
npm install
```

Create a frontend environment file, for example `frontend/.env.local`, with:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXTAUTH_SECRET=<same value used by the backend>
GOOGLE_CLIENT_ID=<google oauth client id>
GOOGLE_CLIENT_SECRET=<google oauth client secret>
```

Start the frontend:

```bash
cd frontend
npm run dev
```

The UI runs at `http://localhost:3000` by default.

## Tests

Run backend tests:

```bash
cd backend
pytest
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

The frontend build requires the frontend environment variables listed above. CI also runs TypeScript checking with `npx tsc --noEmit`.

## Benchmark Testing Flow

With the backend API, worker and frontend running, open `http://localhost:3000/benchmarks`.

Create a benchmark case by entering a suite name, case name, goal and acceptance criteria. Existing suites can also be selected from the form.

Use **Run benchmark** on a case to create a queued benchmark run. Keep the backend worker running so it can claim and execute the run:

```bash
cd backend
python -m app.worker.run_worker
```

After the worker completes the run, refresh the Benchmarks page to view the updated overview and result metrics. **Seed demo benchmarks** remains available as an optional shortcut for sample benchmark data.

## Security Model

- **Authentication:** FastAPI routes use bearer JWT validation with `NEXTAUTH_SECRET`; the frontend uses NextAuth and sends authenticated requests to the backend.
- **Object-level authorization:** run, review, benchmark, configuration and ledger access is scoped by the authenticated user's stable subject where applicable.
- **Filesystem sandboxing:** filesystem paths are normalized and must remain under configured `FILESYSTEM_ALLOWED_PATHS`; unsafe or out-of-scope paths raise sandbox errors.
- **Allowed paths:** defaults are temporary VerifyFlow directories; production-like use should configure explicit allowed directories.
- **Auditability:** ledger entries, task attempts, confidence scores, tool calls, failure records, reviewer decisions and telemetry are persisted to make run outcomes inspectable.
- **No auth bypass for streaming:** run streaming uses authenticated frontend API helpers and backend object checks rather than unauthenticated SSE access.

## Screenshots

Screenshots are not included yet. Suggested additions:

- Dashboard overview
- Run detail with task timeline and telemetry
- Review queue
- Benchmark results

## CI

GitHub Actions workflows are included for:

- Backend tests and Alembic migration validation with PostgreSQL
- Frontend type check, lint and build
- Python and Node dependency security audits

Workflow files live in `.github/workflows/`.

## License

No license file is currently included. Add a `LICENSE` file before publishing or accepting external contributions so users know how the project may be used.

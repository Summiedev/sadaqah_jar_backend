Exit code: 0
Wall time: 1.4 seconds
Output:
# Mizan Backend

The Mizan backend is the FastAPI service for the Mizan Islamic habit, sadaqah,
family, journey, reflection, book, charity, and notification features. It
provides a versioned REST API, WebSocket events, Celery background tasks, and
admin endpoints.

## Capabilities

- JWT authentication, refresh tokens, logout, password changes, and Google OAuth
- Personal sadaqah acts, logs, goals, streaks, badges, dashboards, and leaderboards
- Family jars with invitations, memberships, permissions, goals, milestones, prayers, reflections, and activity
- Journey progress for adhkar, Quran reading, favorites, and reflections
- Books and chapters with admin publishing and evidence management
- Verified donation and charity catalogue data
- In-app notifications and Firebase Cloud Messaging
- Redis caching, deduplication, rate limiting, and WebSocket coordination
- PostgreSQL persistence, Alembic migrations, and MinIO/S3-compatible storage

## Technology

| Area | Technology |
| --- | --- |
| API | FastAPI, Uvicorn, Pydantic v2 |
| Database | PostgreSQL in production, SQLite for tests |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Authentication | JWT, Argon2, Google OAuth |
| Queue | Celery with Redis |
| Cache and rate limits | Redis |
| Push | Firebase Admin SDK / FCM |
| Object storage | MinIO or S3-compatible storage |
| Testing | pytest and FastAPI TestClient |
| Quality | Ruff |
| Deployment | Docker/Podman and an ASGI server |

## Repository layout

```text
app/
  api/              HTTP routers and admin routers
  family/           Family models, repositories, services, and routes
  journey/          Journey domain logic and persistence
  users/            Users, authentication, sessions, and preferences
  notifications/    Notification models, preferences, and deduplication
  books/            Book models and schemas
  models/           Shared SQLAlchemy models
  services/         Cross-domain application services
  tasks/            Celery tasks for notifications and schedules
  core/             Settings, security, cache, WebSockets, and Celery
  db/               SQLAlchemy engine, sessions, and metadata
  seed/             Development and catalogue seed scripts
  tests/            Backend integration and domain tests
alembic/            Database migration history
docker-compose.yml  Local service stack
Dockerfile          Container image definition
pyproject.toml      Dependencies and tool configuration
alembic.ini         Alembic configuration
```

## Architecture

Most domains follow this flow:

```text
HTTP router -> Pydantic schema -> service -> repository -> SQLAlchemy model
                                      |
                                      +-> activity and notification events
```

Routers are thin. Services own validation, authorization, transactions, and
domain rules. Repositories own database access. Responses normally use the
shared envelope from `app/core/envelope.py`.

Family permissions are enforced server-side. The frontend must not be treated
as an authorization boundary.

## Requirements

- Python 3.12 or newer
- PostgreSQL 16 or newer for production
- Redis 7 or newer for production
- Docker or Podman for local infrastructure
- MinIO or S3-compatible storage for uploaded files
- A Firebase service account for production push notifications

## Local setup

From the backend directory:

### 1. Create an environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest ruff
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest ruff
```

If using uv:

```bash
uv sync --frozen
```

### 2. Configure the environment

```bash
cp .env.example .env
```

On Windows:

```powershell
Copy-Item .env.example .env
```

Never commit `.env`, JWT secrets, OAuth secrets, SMTP credentials, or the
Firebase service-account JSON.

### 3. Start infrastructure

```bash
docker compose up -d db redis minio
```

Use `podman compose` when Podman is your runtime.

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Seed development data

Seeding is optional and should normally be used only for development or a
controlled initial deployment:

```bash
python -m app.seed.seed
```

The public charity endpoint only returns records that are verified, active,
and published. An empty donation list can mean seed data is missing or that no
charity has passed all three filters.

## Configuration

Settings are loaded by `app/core/config.py` from environment variables and
the repository `.env` file.

| Variable | Required | Purpose |
| --- | --- | --- |
| `APP_NAME` | Yes | API/application name |
| `ENV` | Yes | `development`, `test`, or `production` |
| `DATABASE_URL` | Yes | PostgreSQL or SQLite SQLAlchemy URL |
| `REDIS_URL` | Yes | Redis broker, cache, and rate-limit URL |
| `JWT_SECRET` | Yes | Unique secret of at least 32 characters |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Access-token lifetime |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `APP_URL` | No | Public URL used in email links |
| `SMTP_HOST` / `SMTP_PORT` | No | Email server configuration |
| `SMTP_USER` / `SMTP_PASSWORD` | No | Email credentials |
| `FROM_EMAIL` | No | Email sender |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `RESEND_API_KEY` | No | Resend email provider key |
| `FCM_SERVICE_ACCOUNT_PATH` | Production | Firebase service-account JSON path |
| `PRAYER_CALCULATION_METHOD` | No | Aladhan method; default is 2 |
| `PRAYER_API_TIMEOUT_SECONDS` | No | External prayer API timeout |

In production, startup fails if `FCM_SERVICE_ACCOUNT_PATH` is missing or
invalid. This prevents push notifications from silently appearing configured
when they cannot be delivered. Development and tests degrade safely to
in-app notifications when FCM is unavailable.

## Running the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful endpoints:

| URL | Purpose |
| --- | --- |
| `/health` | Cheap liveness probe |
| `/readiness` | Database, Redis, and push readiness |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |

`/readiness` returns HTTP 503 when the database or Redis is unavailable.

## Celery

Notification worker:

```bash
celery -A app.core.celery_app worker --loglevel=info -Q notifications
```

Scheduler:

```bash
celery -A app.core.celery_app beat --loglevel=info
```

Event notifications use Redis deduplication and database idempotency keys. If
the broker is temporarily unavailable, the originating family, prayer, goal,
or activity action still completes and the in-app notification is persisted
through a fallback path. Push delivery still requires a healthy worker and
valid Firebase credentials.

## API domains

All versioned routes are under `/api/v1`.

| Prefix | Domain |
| --- | --- |
| `/auth` | Registration, login, refresh, logout, OAuth, and password flows |
| `/users` | Profile, preferences, sessions, and devices |
| `/sadaqah` | Acts, logs, daily acts, goals, streaks, and idempotent writes |
| `/family` | Families, invitations, members, goals, prayers, reflections, and activity |
| `/journey` | Adhkar, Quran progress, favorites, and journey reflections |
| `/books` | Public books, chapters, reading progress, and bookmarks |
| `/charities` | Public verified and published donation catalogue |
| `/notifications` | In-app notifications, preferences, templates, and schedules |
| `/admin/*` | Admin-only management and moderation |
| `/websocket` | Real-time user and family events |

Public charity data is deliberately unauthenticated. Charity creation,
publishing, editing, evidence, and deletion require administrator permissions.

## Database migrations

Check whether model changes require a migration:

```bash
alembic check
```

Create and apply a migration only when the schema changed:

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
```

Review autogenerated migrations manually. Do not use
`Base.metadata.create_all()` as a production migration strategy.

## Testing and quality

Run the complete backend suite:

```bash
pytest -q
```

Run focused suites:

```bash
pytest -q app/tests/test_family.py
pytest -q app/tests/test_notification_delivery.py
```

Compile application modules:

```bash
python -m compileall -q app
```

Lint and format:

```bash
ruff check .
ruff format --check .
```

Tests use an isolated SQLite database under `.pytest_tmp`. Celery is eager in
the test process so notification behavior is tested without a live Redis
worker. Production remains broker-backed.

## Docker deployment

Typical deployment sequence:

```bash
docker compose build
docker compose up -d db redis minio
docker compose run --rm app alembic upgrade head
docker compose up -d app worker beat
```

Before exposing the API:

1. Set a strong unique `JWT_SECRET`.
2. Set restrictive `CORS_ORIGINS`.
3. Mount the Firebase service-account file securely.
4. Run `/readiness` and confirm database, Redis, and push status.
5. Confirm charity seed or admin-published donation records exist.
6. Verify worker and beat logs.
7. Put the API behind HTTPS and a reverse proxy.

## Operational notes

- `/health` confirms that the process is alive; it does not prove dependencies are ready.
- `/readiness` is the deployment/load-balancer dependency probe.
- Redis is required in production for rate limiting, deduplication, caching, and Celery.
- Push requires valid FCM configuration and registered device tokens.
- In-app notifications can still be persisted when push delivery is unavailable.
- Charity records must be verified, active, and published to appear publicly.
- File URLs may be signed MinIO/S3 URLs and should not be treated as permanent.
- Soft-deleted records should not be restored with direct SQL edits.
- Admin endpoints must never be exposed without authentication and role enforcement.

## Adding a feature

1. Add or update the domain model.
2. Add repository database access.
3. Add service validation and authorization.
4. Add Pydantic schemas.
5. Add a thin router endpoint.
6. Add activity and notification events where appropriate.
7. Add a migration only if the schema changed.
8. Add tests for success, authorization, duplicate requests, failures, and retries.
9. Run `alembic check`, `pytest`, `ruff check`, and relevant frontend tests.

## License

No `LICENSE` file is currently included in this repository.

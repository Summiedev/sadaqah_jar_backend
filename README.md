# Mizan Backend

FastAPI backend for the Mizan sadaqah and habit-tracking app. Provides REST APIs and WebSocket support for user management, sadaqah act tracking, family collaboration, journey (adhkar) guides, book reading, and push notifications.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI (async, OpenAPI auto-docs)
- **Database:** PostgreSQL (production), SQLite (tests)
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Cache/Queue:** Redis + Celery
- **Auth:** JWT (python-jose + passlib/argon2), Google OAuth 2.0
- **Validation:** Pydantic v2
- **Rate Limiting:** slowapi + Redis
- **Push Notifications:** Firebase Cloud Messaging (firebase-admin)
- **File Storage:** MinIO (S3-compatible)
- **Testing:** pytest
- **Linting/Formatting:** ruff
- **Deployment:** Docker/Podman, Caddy reverse proxy, uvicorn ASGI server

## Project Structure

```
sadaqah_jar_backend/
├── app/
│   ├── api/                 # HTTP route handlers (one file per domain)
│   │   ├── router.py        # Central API router — includes all sub-routers
│   │   ├── sadaqah.py       # Personal sadaqah acts, daily acts, streaks, logs
│   │   ├── adhkar.py        # Adhkar (remembrance) tracking
│   │   ├── friday.py        # Friday-specific adhkar & boosts
│   │   ├── dashboard.py     # Dashboard stats and heatmap
│   │   ├── leaderboard.py   # Global and family leaderboards
│   │   ├── streak.py        # Personal streak data
│   │   ├── badges.py        # Badge catalog
│   │   ├── charities.py     # Verified charity list
│   │   ├── books.py         # Book catalog endpoints
│   │   ├── admin_*.py       # Admin panel endpoints (analytics, evidence, etc.)
│   │   └── websocket.py     # WebSocket endpoint for real-time updates
│   │
│   ├── family/              # Family jar domain
│   │   ├── models.py        # Family, FamilyMember, FamilyGoal, FamilyActivity, etc.
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── service.py       # Business logic, permissions, activity logging
│   │   ├── repository.py    # Database access layer
│   │   ├── router.py        # HTTP endpoints for family operations
│   │   └── exceptions.py    # Domain-specific exceptions
│   │
│   ├── core/                # Cross-cutting concerns
│   │   ├── config.py        # Settings (env vars) via pydantic-settings
│   │   ├── auth.py          # JWT creation/verification
│   │   ├── security.py      # Password hashing, token helpers
│   │   ├── dependencies.py  # Shared request dependencies (DB, current user)
│   │   ├── envelope.py      # Response envelope pattern
│   │   ├── cache.py         # Redis caching utilities
│   │   ├── ws_manager.py    # WebSocket connection manager
│   │   ├── rate_limit.py    # Redis-backed rate limiting
│   │   └── ...
│   │
│   ├── db/                  # Database setup
│   │   ├── base.py          # SQLAlchemy Base
│   │   ├── deps.py          # Session dependency injection
│   │   ├── session.py       # Engine and session factory
│   │   └── test_db.py       # Test database helpers
│   │
│   ├── models/              # Shared/legacy models (Jar, SadaqahAct, etc.)
│   ├── users/               # User auth, profile, permissions
│   ├── goals/               # Goal tracking
│   ├── journey/             # Journey/adhkar progress
│   ├── books/               # Book catalog (admin-managed)
│   ├── notifications/       # Push notification templates and scheduling
│   ├── seed/                # Database seeding scripts
│   ├── services/            # Business logic services (streaks, badges, prayer time, etc.)
│   ├── tasks/               # Celery scheduled tasks (daily acts, reminders)
│   └── utils/               # Shared helpers (invite codes, constants)
│
├── alembic/                 # Database migration scripts
├── docker-compose.yml       # Local dev stack (Postgres, Redis, MinIO, Caddy)
├── Dockerfile               # Production image
├── pyproject.toml           # Project config, dependencies, pytest settings
├── requirements.txt         # Pinned dependencies
├── Caddyfile                # Reverse proxy config
├── alembic.ini              # Alembic configuration
└── conftest.py              # Top-level pytest config
```

## Architecture

The backend follows a **layer-first domain structure** within each module:

1. **Models** (`models.py`) — SQLAlchemy ORM definitions with soft delete, timestamps, and versioning
2. **Repository** (`repository.py`) — Pure database access, no business logic
3. **Service** (`service.py`) — Business logic, authorization, and activity logging
4. **Router** (`router.py`) — Thin HTTP layer that calls services and returns envelopes
5. **Schemas** (`schemas.py`) — Pydantic request/response models

All API responses follow the **envelope pattern** (`Envelope` from `app/core/envelope.py`) for consistent front-end consumption. The permission system maps roles (OWNER, ADMIN, MEMBER) to action scopes (e.g., `CREATE_PRAYER`, `MANAGE_GOALS`).

## Prerequisites

- **Python:** >= 3.12
- **PostgreSQL:** 16 (production), SQLite for tests
- **Redis:** 7 (cache + Celery broker + rate limiting)
- **MinIO** (optional, for file/evidence storage)

## Installation

```bash
# Clone
cd sadaqah_jar_backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (preferred method)
uv sync --frozen

# Or with pip
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env — see Environment Variables below

# Run migrations
alembic upgrade head

# (Optional) Seed the database
python -m app.seed.seed
```

## Environment Variables

All configuration is in `app/core/config.py` (`Settings` class, reads from `.env`).

| Variable | Required | Description |
|---|---|---|
| `APP_NAME` | Yes | Application name |
| `ENV` | Yes | `development` or `production` |
| `DATABASE_URL` | Yes | PostgreSQL DSN (e.g. `postgresql+psycopg2://user:pass@host:5432/mizan`) |
| `REDIS_URL` | Yes | Redis URL (e.g. `redis://localhost:6379/0`) |
| `JWT_SECRET` | Yes | Signing secret for JWT tokens (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | JWT token lifetime in minutes |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `SMTP_HOST` / `SMTP_PORT` | No | SMTP server for verification/password-reset emails |
| `FROM_EMAIL` | No | Email sender address |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `RESEND_API_KEY` | No | Resend email API key |
| `FCM_SERVICE_ACCOUNT_PATH` | No | Path to Firebase service account JSON (blank = push disabled) |
| `PRAYER_CALCULATION_METHOD` | No | Aladhan method ID (2 = ISNA, default) |
| `APP_URL` | No | Public base URL for email links |

**Important:** Never commit real `JWT_SECRET`, SMTP credentials, or Google/Resend API keys. The `FCM_SERVICE_ACCOUNT_PATH` must point to a valid Firebase service account JSON for push notifications to function; leaving it blank disables push delivery entirely.

## Running the Project

### Development

```bash
# Start the API with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

### Docker / Podman

```bash
# Start all services (Postgres, Redis, MinIO, Caddy, app)
podman-compose up -d
# or: docker compose up -d
```

The app runs on port 8000 behind Caddy (port 80/443) at `api.sad-aqah.app`.

## Testing

```bash
# Run all tests (excludes test_daily_acts.py per pyproject.toml)
pytest

# Run a specific test file
pytest app/tests/test_family.py -v

# With coverage
pytest --cov=app
```

Tests use an **in-memory SQLite database** (configured in `conftest.py` — creates `.pytest_tmp/test.db`). No external database is needed for tests.

## Running Celery Tasks

```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

Scheduled tasks include daily act generation, prayer reminders, and Friday boost processing.

## API Endpoints

All routes prefixed with `/api/v1`:

| Prefix | Domain | Notes |
|---|---|---|
| `/auth/` | Authentication | Login, register, token refresh, Google OAuth |
| `/users/` | User management | Profile, role changes |
| `/sadaqah/` | Sadaqah tracking | Acts, daily acts, streaks, logs |
| `/family/` | Family jars | Create/join families, goals, prayers, reflections, activities |
| `/journey/` | Journey | Adhkar progress, reflections |
| `/books/` | Books | Catalog (admin-managed) |
| `/dashboard/` | Dashboard | Stats, heatmap |
| `/badges/` | Badges | Badge catalog |
| `/charities/` | Charities | Verified organizations |
| `/notifications/` | Notifications | Templates and scheduled pushes |
| `/admin/` | Admin | Analytics, evidence, leaderboard seasons |
| `/websocket/` | WebSocket | Real-time family updates |

## Contributing

1. Lint: `ruff check .`
2. Format: `ruff format .`
3. Test: `pytest`
4. Migrations: `alembic revision --autogenerate -m "description"` then `alembic upgrade head`
5. Add new domain modules under `app/` following the existing pattern

## Known Limitations

- **No per-user book reading progress table** — the "Continue reading" feature in the frontend is UI-only; the backend seeds book/chapter data but does not persist per-user reading position (see `app/seed/seed.py` comment).
- **Push notifications are no-op** when `FCM_SERVICE_ACCOUNT_PATH` is not set (the service returns `None` for Firebase messaging and skips delivery).
- Celery task triggers require an external scheduler (system cron or container orchestrator).
- Rate limiting depends on Redis being available in production.

## License

No LICENSE file found in the project.
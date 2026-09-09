# Corvus backend

The Corvus backend is a FastAPI service responsible for authentication,
authorization, persistence, and workout-domain business rules.

The API implements registration, access/refresh-token authentication, an exercise
catalog, and private workout templates with ordered exercises and planned sets.
Workout sessions, history, and progress endpoints are not implemented yet.

See [API.md](API.md) for request examples, validation, PATCH semantics, and errors.

## Available endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `POST` | `/auth/register` | Create a user account |
| `POST` | `/auth/login` | Sign in and create a refresh session |
| `POST` | `/auth/refresh` | Rotate the refresh session and issue an access token |
| `GET` | `/auth/me` | Return the authenticated user |
| `POST` | `/auth/logout` | Revoke the current refresh session |
| `GET` | `/muscle-groups` | Read the muscle-group catalog |
| `GET` | `/exercises` | List system and own exercises |
| `POST` | `/exercises` | Create a personal exercise |
| `GET` | `/workout-templates` | List own templates |
| `POST` | `/workout-templates` | Create a template with exercises and sets |
| `GET` | `/workout-templates/{template_id}` | Read an owned template |
| `PATCH` | `/workout-templates/{template_id}` | Update an owned template |
| `DELETE` | `/workout-templates/{template_id}` | Delete an owned template |

OpenAPI documentation is available at `/docs` while the application is
running; the generated schema is at `/openapi.json`. There is no `/api` prefix.
All exercise, muscle-group, and template routes require a Bearer access token.

## Structure

```text
backend/
├── app/
│   ├── api/             routers and request dependencies
│   ├── core/            configuration and security
│   ├── db/              SQLAlchemy models and sessions
│   ├── repositories/    persistence operations
│   ├── schemas/         Pydantic request and response models
│   ├── services/        business logic
│   └── main.py          FastAPI application
├── migrations/          Alembic migrations
├── scripts/             development helper scripts
└── tests/               API, service, schema, and database tests
```

`app/api/router.py` collects the auth, exercise, and template routers.
`main.py` includes that router and defines `/health`. Services coordinate
transactions; repositories perform database queries and flush changes.

## Run with Docker Compose (Git Bash)

Run commands from `backend/`, where `compose.yaml` lives. For a new environment,
copy the example configuration; do not overwrite an existing `.env`:

```bash
cp .env.example .env
```

Set secure values for `POSTGRES_PASSWORD` and `CORVUS_JWT_SECRET_KEY`, then run:

```bash
docker compose up --build
```

Compose starts PostgreSQL, applies all Alembic migrations, and serves the API
at `http://localhost:8000` by default.

Stop the services with:

```bash
docker compose down
```

The PostgreSQL data remains in the `postgres_data` Docker volume.
Use `docker compose logs -f app` to inspect startup errors. To run from the
repository root instead, use:

```bash
docker compose --env-file backend/.env -f backend/compose.yaml up --build
```

## Run locally

Python 3.13 is used by the backend container.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-dev.txt
```

These activation instructions are for Windows Git Bash. On Linux/macOS use
`source .venv/bin/activate`. Create `.env` if needed and update
`CORVUS_DATABASE_URL` to match the configured PostgreSQL user, password, and
published port, using host `localhost`. Compose supplies its own URL using `db`.

Start PostgreSQL through Compose, apply migrations, and run FastAPI:

```bash
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

## Configuration

Settings use the `CORVUS_` prefix and can be supplied through environment
variables or `backend/.env`.

Important values:

| Variable | Description |
| --- | --- |
| `CORVUS_DATABASE_URL` | SQLAlchemy database connection URL |
| `CORVUS_JWT_SECRET_KEY` | Secret used to sign JWTs |
| `CORVUS_DEBUG` | Enables local debug behavior |
| `CORVUS_CORS_ORIGINS` | JSON list of allowed frontend origins |
| `CORVUS_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime |
| `CORVUS_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-session lifetime |

Never commit `backend/.env` or use the example secrets in production.

Refresh cookies are HttpOnly, SameSite=Lax, scoped to `/auth`, and Secure when
debug is false. For local HTTP development, set `CORVUS_DEBUG=true` if needed
for cookie handling. Production should use HTTPS and debug false.

Compose uses `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and
`POSTGRES_PORT` for the database, and `BACKEND_PORT` for the API port (default
8000). It forwards only the settings listed in `app.environment` in
`compose.yaml`. To override token lifetimes inside the container, add those
variables there too; host `.env` entries alone are not automatically forwarded.

## Database migrations

Apply migrations:

```bash
alembic upgrade head
```

Create a migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the change"
```

Review generated migrations before applying them. Existing migration history
should not be rewritten.

## Tests and quality checks

Run the unit suite without requiring PostgreSQL:

```bash
python scripts/run_unit_tests.py
```

Run all configured tests:

```bash
pytest
```

Run formatting and lint checks:

```bash
ruff check .
ruff format --check .
```

Run these commands from `backend/` with the virtual environment activated.
Tests use in-memory SQLite; they do not replace PostgreSQL migration checks.
Template tests cover validation, ownership, nested persistence, PATCH,
cascading deletion, and transaction rollback.

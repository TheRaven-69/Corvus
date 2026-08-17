# Corvus backend

The Corvus backend is a FastAPI service responsible for authentication,
authorization, persistence, and workout-domain business rules.

The current API slice implements user registration and access/refresh-token
authentication. Workout resources will be added incrementally as the MVP grows.

## Available endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `POST` | `/auth/register` | Create a user account |
| `POST` | `/auth/login` | Sign in and create a refresh session |
| `POST` | `/auth/refresh` | Rotate the refresh session and issue an access token |
| `GET` | `/auth/me` | Return the authenticated user |
| `POST` | `/auth/logout` | Revoke the current refresh session |

OpenAPI documentation is available at `/docs` while the application is
running.

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

## Run with Docker Compose

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Set secure values for `POSTGRES_PASSWORD` and `CORVUS_JWT_SECRET_KEY`, then run:

```powershell
docker compose up --build
```

Compose starts PostgreSQL, applies all Alembic migrations, and serves the API
at `http://localhost:8000` by default.

Stop the services with:

```powershell
docker compose down
```

The PostgreSQL data remains in the `postgres_data` Docker volume.

## Run locally

Python 3.13 is used by the backend container.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Start PostgreSQL through Compose, apply migrations, and run FastAPI:

```powershell
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

## Database migrations

Apply migrations:

```powershell
alembic upgrade head
```

Create a migration after changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe the change"
```

Review generated migrations before applying them. Existing migration history
should not be rewritten.

## Tests and quality checks

Run the unit suite without requiring PostgreSQL:

```powershell
python scripts/run_unit_tests.py
```

Run all configured tests:

```powershell
pytest
```

Run formatting and lint checks:

```powershell
ruff check .
ruff format --check .
```

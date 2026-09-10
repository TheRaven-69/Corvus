# Corvus

Corvus is a workout planning and tracking application for people who want a
structured alternative to notes and spreadsheets. It is an early MVP: account
management, exercises, and reusable workout templates are implemented across
the API and frontend. Performing and recording a workout is not implemented yet.

## Current implementation

| Capability | Status |
| --- | --- |
| Registration, sign-in, session restoration, sign-out | Implemented |
| Access tokens and rotating HttpOnly refresh-cookie sessions | Implemented |
| System/personal exercise catalog and personal exercise creation | Implemented |
| Private workout-template creation, listing, editing, deletion | Implemented |
| Ordered exercises and planned sets, reps, weight, notes | Implemented |
| English/Ukrainian UI and responsive navigation | Implemented |
| Dashboard metrics and charts | Empty UI placeholders |
| Start/record/complete workout sessions | Not implemented |
| Workout history and exercise progress | Not implemented |
| Achievements and settings flows | Not implemented |

The template builder includes an exercise library, individual exercise cards,
warm-up/working sets, validation, a live plan summary, and unsaved-change guards.
Desktop navigation collapses to an icon rail using the Corvus brand control;
mobile navigation is fixed at the bottom. All implemented screens share the
warm, dark-and-gold visual direction from the supplied Figma Make reference.

The next MVP milestone is starting a session from a template, recording completed
sets, and completing it. History and exercise progress follow that flow.

## Technology and structure

- Backend: Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Pytest.
- Frontend: React, TypeScript, Vite, i18next, Phosphor Icons, plain CSS.
- Checks: Ruff for backend; Vitest/Testing Library, Oxlint, and TypeScript for frontend.
- Development: Docker Compose for PostgreSQL/API; Vite for frontend.
- GitHub Actions: separate backend and frontend quality workflows.

```text
Corvus/
├── backend/              FastAPI, migrations, tests, compose.yaml
├── frontend/             React client, styles, and behavior tests
├── docs/reviews/          review notes (historical findings and follow-ups)
├── .github/workflows/    backend and frontend CI
└── README.md
```

Detailed guides: [backend README](backend/README.md),
[frontend README](frontend/README.md), and [API contract](backend/API.md).
Local `PRODUCT.md` and `DESIGN.md`, when present, are planning/design notes and
are not required to run the application.

## Quick start

Install Docker with Compose and Node.js 24 (the version used by frontend CI).
The commands below use PowerShell; in Bash use `npm` instead of `npm.cmd`.

### Backend

From the repository root, create configuration only if it does not exist:

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Set `POSTGRES_PASSWORD` and `CORVUS_JWT_SECRET_KEY` in `backend/.env`. For local
HTTP development use `CORVUS_DEBUG=true`. Then:

```powershell
cd backend
docker compose up --build
```

Compose starts PostgreSQL, applies Alembic migrations, and starts the API.
Default endpoints are [API health](http://localhost:8000/health) and
[interactive API documentation](http://localhost:8000/docs). Routes have no
`/api` prefix. Compose is located in `backend/`, not at the repository root.

### Frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.
The frontend API default is `http://localhost:8000`; customize
`VITE_API_BASE_URL` in `frontend/.env.local` when needed. Allow the actual
frontend origin in backend `CORVUS_CORS_ORIGINS`, and use matching local
hostnames for cookie authentication. Restart Vite after changing its environment.

Create an account, sign in, browse or create exercises, then build a template.
Workout-start controls remain disabled until session recording is implemented.

Do not commit `.env` files or use example secrets in production. Refresh cookies
are HttpOnly and become Secure when backend debug is false; production requires
HTTPS. The development Compose configuration is not a production deployment guide.

## Checks

Backend, from `backend/` with its Python environment and development dependencies
installed (see its README):

```powershell
python scripts/run_unit_tests.py
python -m ruff check .
python -m ruff format --check .
```

Frontend, from `frontend/`:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

CI runs these respective quality checks. Backend coverage includes API,
authorization, schemas, services, and persistence behavior. Frontend tests cover
rendered behavior with mocked HTTP responses, including template editing and
keyboard interactions. There is no committed full-stack browser E2E or visual
regression suite; a passing frontend suite does not verify a live API deployment.

## Scope

Complete the personal workout flow before adding platform features. Coach roles,
nutrition, AI recommendations, and gym management are future ideas, not current
MVP capabilities. Historical sessions must eventually remain stable when their
source template changes; that is a requirement for the upcoming session feature,
not a claim that session history already exists.

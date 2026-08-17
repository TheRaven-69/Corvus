# Corvus

Corvus is a workout planning and tracking application for people who want a
structured alternative to notes, spreadsheets, and generic fitness apps.

The project is currently an early MVP. The implemented vertical slice covers
registration, sign-in, session restoration, sign-out, localization, and a
responsive dashboard shell with honest empty states.

## Current features

- account registration and sign-in;
- short-lived access tokens and rotating refresh sessions;
- secure HttpOnly refresh cookies;
- English and Ukrainian interface;
- responsive authentication and dashboard screens;
- explicit empty and unavailable states instead of fabricated workout data;
- backend tests and frontend behavior tests.

The next product areas are exercises, workout templates, workout sessions,
history, and exercise progress.

## Technology

### Backend

- Python, FastAPI, and Pydantic;
- SQLAlchemy 2 and Alembic;
- PostgreSQL;
- Pytest.

### Frontend

- TypeScript and React;
- Vite and Vitest;
- i18next;
- Phosphor Icons.

## Repository structure

```text
Corvus/
├── backend/       FastAPI application, migrations, and tests
├── frontend/      React application and frontend tests
├── PRODUCT.md     durable product direction
└── DESIGN.md      shared visual design system
```

More detailed setup notes are available in
[backend/README.md](backend/README.md) and
[frontend/README.md](frontend/README.md).

## Quick start

### 1. Start the backend

Docker Desktop or another Docker Compose environment is the simplest option.

```powershell
Copy-Item backend/.env.example backend/.env
```

Replace `POSTGRES_PASSWORD` and `CORVUS_JWT_SECRET_KEY` in `backend/.env`, then:

```powershell
Set-Location backend
docker compose up --build
```

The API will be available at `http://localhost:8000`. Interactive OpenAPI
documentation is available at `http://localhost:8000/docs`.

### 2. Start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

## Checks

Backend:

```powershell
Set-Location backend
python scripts/run_unit_tests.py
ruff check .
ruff format --check .
```

Frontend:

```powershell
Set-Location frontend
npm test
npm run lint
npm run build
```

## Project scope

Corvus intentionally focuses on the core personal workout flow first. Coach
roles, nutrition, recommendations, and other platform features are future ideas
and are not part of the current MVP.

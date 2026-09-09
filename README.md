# Corvus

Corvus is a workout planning and tracking application for people who want a
structured alternative to notes, spreadsheets, and generic fitness apps.

The project is currently an early MVP. The implemented vertical slice covers
registration, sign-in, session restoration, sign-out, localization, and a
responsive dashboard shell with honest empty states. The exercise catalog is
integrated into the frontend; the backend also provides workout-template CRUD.

## Current features

- account registration and sign-in;
- short-lived access tokens and rotating refresh sessions;
- secure HttpOnly refresh cookies;
- English and Ukrainian interface;
- responsive authentication and dashboard screens;
- explicit empty and unavailable states instead of fabricated workout data;
- backend tests and frontend behavior tests.
- system and personal exercises with localized names and muscle groups;
- backend workout templates with ordered exercises, planned sets, repetitions,
  and weights, including owner-only editing and deletion.

Next are the workout-template frontend, workout sessions, history, and exercise
progress. Template UI and session recording are not implemented yet.

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
└── README.md      setup and implementation status
```

More detailed setup notes are available in
[backend/README.md](backend/README.md) and
[frontend/README.md](frontend/README.md).
The [backend API guide](backend/API.md) describes authentication, payloads,
PATCH behavior, and errors. Local `PRODUCT.md` and `DESIGN.md` files, when present,
contain planning/design notes and are not required for setup.

## Quick start

### 1. Start the backend

Docker Desktop or another Docker Compose environment is the simplest option.

Commands below use Git Bash. For a new environment (preserve an existing `.env`):

```bash
cp backend/.env.example backend/.env
```

Replace `POSTGRES_PASSWORD` and `CORVUS_JWT_SECRET_KEY` in `backend/.env`, then:

```bash
cd backend
docker compose up --build
```

The API will be available at `http://localhost:8000`. Interactive OpenAPI
documentation is available at `http://localhost:8000/docs`.

### 2. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

## Checks

Backend (from the repository root, with its Python environment activated):

```bash
cd backend
python scripts/run_unit_tests.py
ruff check .
ruff format --check .
```

Frontend (from the repository root):

```bash
cd frontend
npm test
npm run lint
npm run build
```

## Project scope

Corvus intentionally focuses on the core personal workout flow first. Coach
roles, nutrition, recommendations, and other platform features are future ideas
and are not part of the current MVP.

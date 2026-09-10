# Corvus frontend

React and TypeScript client for the current Corvus MVP: accounts, an exercise
catalog, and reusable workout templates. Workout recording is the next vertical
slice; the dashboard is currently a shell with explicit empty states.

## Implemented screens and flows

- Registration, sign-in, session restoration, and sign-out.
- English and Ukrainian UI with a persisted language choice.
- Dashboard navigation: the Corvus brand control expands/collapses the desktop
  sidebar into an icon rail. On screens up to 48rem, the three available
  destinations (Dashboard, Templates, Exercises) appear in a fixed bottom bar.
  Sidebar state is held in component memory, not persisted across reloads.
- Exercise catalog with client-side search, localized names, muscle groups,
  and personal exercise creation.
- Template listing, creation, editing, and confirmed deletion.
- Workout builder with name/description, ordered exercise cards, warm-up and
  working sets, repetition targets, optional weight, and exercise notes.
- Exercise library beside the plan on wide screens and below it on narrower
  screens; the save area summarizes exercise and planned-set counts.
- Field-level validation, focus on invalid inputs, focus restoration after
  removal, and confirmation before leaving an unsaved template.

Workout-start controls are disabled. Sessions, completed sets, history,
progress, achievements, and settings are not functional product flows yet.
Dashboard totals and charts are empty placeholders, not training analytics.

## Stack

React, TypeScript, Vite, i18next/react-i18next, Phosphor Icons, and plain CSS.
Vitest and Testing Library cover behavior; Oxlint provides linting.
There is no client-side routing library: Dashboard selects its view in React
state, so individual screens do not currently have deep-link URLs.

## Local development

Use Node.js 24 to match frontend CI. Start the API using the
[backend setup guide](../backend/README.md), then run from `frontend/`:

```powershell
npm.cmd ci
npm.cmd run dev
```

In Bash, use `npm` instead of `npm.cmd`. Open the URL printed by Vite,
normally `http://localhost:5173`.

The API defaults to `http://localhost:8000`. To change it, copy `.env.example`
to `.env.local` without overwriting existing configuration, set
`VITE_API_BASE_URL`, and restart Vite. The URL has no `/api` suffix.
Never put secrets in `VITE_` variables: they are exposed in the browser bundle.

Requests include credentials. The frontend origin must be allowed by backend
`CORVUS_CORS_ORIGINS`. Use matching hostnames for local frontend and API
(for example, both `localhost`); switching one to `127.0.0.1` can affect cookies.
Local HTTP development uses `CORVUS_DEBUG=true` on the backend so refresh
cookies are not Secure-only. Production requires HTTPS and debug disabled.

## Code map

```text
frontend/
├── src/
│   ├── main.tsx                  React entry point and font/style imports
│   ├── App.tsx                   authentication/session state
│   ├── App.css                   auth screens and shared interaction styles
│   ├── index.css                 global design tokens and base styles
│   ├── i18n.ts                   language setup and shared translations
│   ├── api/
│   │   ├── http.ts               fetch, API base URL, and ApiError
│   │   ├── auth.ts               auth, refresh, and authenticated retry
│   │   ├── exercises.ts          exercise and muscle-group contracts
│   │   └── workoutTemplates.ts   template API contracts and requests
│   ├── components/              brand and language controls
│   ├── features/
│   │   ├── auth/                login and registration forms
│   │   ├── dashboard/           navigation and dashboard shell
│   │   ├── exercises/           catalog and exercise creation
│   │   └── templates/
│   │       ├── TemplatesPage.tsx list, loading, errors, CRUD orchestration
│   │       ├── TemplateEditor.tsx workout builder
│   │       ├── templateDraft.ts  draft conversion and validation
│   │       ├── translations.ts  English/Ukrainian template strings
│   │       └── TemplatesPage.css template and builder styles
│   └── test/setup.ts            test matcher setup
├── vite.config.ts
├── vitest.config.ts
└── package.json
```

## Authentication and API behavior

Registration returns to sign-in with the account information prefilled; it
does not create an authenticated session. Login obtains an access token and
loads `/auth/me`. The access token stays in memory. Reloading restores the
session through the backend's HttpOnly refresh cookie and `/auth/refresh`.

`apiRequestWithAuth` retries a protected request once after refreshing on a
401. Exercise and template clients use this helper. `apiRequest` itself does
not retry. Backend authorization remains authoritative for private data.

Template weights are decimal strings; an empty weight becomes `null`.
Metadata-only PATCH requests omit exercises to avoid replacing their rows.
Exercise and set order are sent explicitly. Template drafts are not persisted
locally: navigation/logout is guarded, and closing or reloading the page uses
the browser's unsaved-change warning while a draft is dirty or saving.

See [backend/API.md](../backend/API.md) for the actual payloads and errors.

## Visual system and localization

The supplied Figma Make direction is shared across implemented screens: warm
canvas, white surfaces, dark navigation, gold accents, and self-hosted DM Sans.
Unsupported glyphs, including Cyrillic, use the configured sans-serif fallback.
Shared tokens are in `src/index.css`; feature CSS handles layouts. Controls have
hover, pressed, and visible keyboard-focus states. Hover styling is gated to
fine pointers and reduced-motion preferences are respected.

New copy needs both English and Ukrainian translations. Shared strings live
in `src/i18n.ts`; template strings live in `features/templates/translations.ts`
and are merged into those resources. Language is stored as `corvus.language`
in localStorage and synchronized with the document's `lang` attribute.

## Checks and coverage

Run from `frontend/`:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

`build` runs TypeScript checks and emits the production bundle into `dist/`.
`npm.cmd run preview` serves that build locally; it is not a production server.
Frontend CI runs `npm ci`, lint, tests, and build on Node.js 24.

Behavior tests live in `src/App.test.tsx`,
`src/features/dashboard/Dashboard.test.tsx`, and
`src/features/templates/TemplatesPage.test.tsx`. They cover authentication,
exercise flows, menu keyboard toggling, template CRUD, ordering, validation,
API errors, unsaved-change handling, focus, and builder counts.

HTTP responses are mocked. These tests do not establish full end-to-end
compatibility with a live backend or verify pixel appearance. Responsive and
visual checks are performed separately in the browser; there is no committed
full-stack browser E2E or visual regression suite yet.

# Corvus frontend

A React client for Corvus. The current vertical slice covers registration,
sign-in, session restoration, sign-out, and an authenticated dashboard shell.

## Project structure

```text
frontend/
├── index.html                 HTML entry point containing #root
├── src/
│   ├── main.tsx               mounts React and renders App
│   ├── App.tsx                session state and root-level UI selection
│   ├── api/
│   │   ├── http.ts            shared fetch wrapper
│   │   └── auth.ts            auth request types and API functions
│   ├── features/auth/
│   │   ├── AuthPanel.tsx      sign-in and registration mode selection
│   │   ├── LoginForm.tsx      sign-in form and request states
│   │   └── RegisterForm.tsx   registration form and validation
│   ├── features/dashboard/
│   │   └── Dashboard.tsx      authenticated dashboard shell
│   ├── App.test.tsx           behavior-focused authentication tests
│   └── test/setup.ts          test matcher setup
├── vite.config.ts             development server and build configuration
├── vitest.config.ts           test configuration
└── package.json               dependencies and npm scripts
```

## Authentication flow

1. `LoginForm` stores input values with `useState`.
2. Submit calls `login()` from `src/api/auth.ts`.
3. `apiRequest()` sends `POST /auth/login` with `credentials: 'include'` so
   the browser can receive the HttpOnly refresh cookie.
4. The returned access token is sent to `GET /auth/me` as a Bearer token.
5. `App` receives the user and renders the dashboard.

The access token exists only in page memory. When the page reloads, `App`
calls `POST /auth/refresh`; the browser sends the HttpOnly cookie and the
frontend retrieves the user again through `GET /auth/me`.

The backend does not create an authenticated session during registration, so
the frontend returns the user to a prefilled sign-in form after account
creation.

Password confirmation is validated only in the browser. The confirmation
value is not sent to the API, so the backend `UserRegister` contract remains
unchanged.

The authenticated dashboard follows the intended Corvus information
architecture. Workout actions that are not implemented yet are explicitly
disabled and marked as coming soon.

Automatic retry of arbitrary protected requests after an access token expires
is not implemented yet. It should be added with the first protected workout API
integration rather than introduced as a premature abstraction.

## Localization

Corvus uses `i18next` with `react-i18next`. English is the default language and
Ukrainian can be selected with the `EN / UK` control. The selection is stored
under `corvus.language` in `localStorage`, and the page `<html lang>` attribute
is updated with it.

User-facing text belongs in `src/i18n.ts`, not directly in components. Add both
English and Ukrainian values for every new translation key so future screens
remain complete in both languages.

## Local development

The backend should run at `http://localhost:8000`. Then run these commands in
the frontend directory:

```powershell
npm.cmd install
npm.cmd run dev
```

Vite will print the application URL, usually `http://localhost:5173`.

If the backend uses another address, copy `.env.example` to `.env.local` and
change `VITE_API_BASE_URL`. Do not commit `.env.local`.

## Checks

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

- `test` verifies behavior from the user's perspective;
- `lint` finds suspicious code patterns;
- `build` runs TypeScript checks and produces the production bundle.

## Suggested learning order

1. `src/main.tsx` — how React mounts into the page.
2. `src/App.tsx` — components, state, effects, and conditional rendering.
3. `src/features/auth/LoginForm.tsx` — controlled inputs and async submit.
4. `src/features/auth/RegisterForm.tsx` — multiple fields and validation.
5. `src/features/auth/AuthPanel.tsx` — props and component selection.
6. `src/api/auth.ts` — request and response types.
7. `src/api/http.ts` — fetch and HTTP error handling.
8. `src/features/dashboard/Dashboard.tsx` — composed page layout.
9. `src/App.test.tsx` — testing behavior without a live backend.

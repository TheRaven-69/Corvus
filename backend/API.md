# Corvus API usage

Base URL: `http://localhost:8000` by default, without an `/api` prefix.
See [README.md](README.md) for the full route inventory and setup.
Interactive schemas are at `/docs`; the generated contract is `/openapi.json`.

## Authentication in Swagger

Register with `email`, `username`, `first_name`, `last_name`, and `password`.
Registration returns 201 but does not sign in automatically. Login accepts an
email or username in `login`:

```json
{"login": "owner@example.com", "password": "your-password"}
```

Copy `access_token` from the login response into **Authorize**, without `Bearer`.
Other clients send `Authorization: Bearer <access_token>`.
The refresh token is an HttpOnly cookie scoped to `/auth`, not a token to paste
into Authorize. Browser clients use `credentials: "include"` for cookies.
`POST /auth/refresh` rotates the session and issues a new access token; replace
the access token in Swagger after refreshing. Logout revokes the refresh session
and clears the cookie, returning 204.

## Exercise catalog

`GET /muscle-groups` returns objects with `code` and localized `names`.
`GET /exercises` returns system exercises and the current user's personal ones.
Both require authentication. To create a personal exercise, POST to `/exercises`:

```json
{
  "name": "Dumbbell bench press",
  "locale": "en",
  "muscle_group_codes": ["chest", "triceps"]
}
```

Use codes actually present in your database. Names are nonblank, trimmed, and
limited to 120 characters. Locale is `en` or `uk`; provide 1–10 unique muscle-group
codes. Unknown codes return 422. Success returns 201 and an exercise with `id`,
nullable `code`, localized `names`, `muscle_groups`, `created_at`, and `updated_at`.
There are no exercise edit/delete endpoints yet.

## Create a template

Send `POST /workout-templates`. Replace the sample UUID with an accessible ID
from `GET /exercises`:

```json
{
  "name": "Push day",
  "description": "Chest and triceps",
  "exercises": [
    {
      "exercise_id": "11111111-1111-4111-8111-111111111111",
      "position": 0,
      "notes": "Controlled tempo",
      "sets": [
        {"position": 0, "set_type": "warmup", "target_reps": 10, "target_weight_kg": "20.00"},
        {"position": 1, "set_type": "working", "target_reps": 8, "target_weight_kg": "42.50"}
      ]
    }
  ]
}
```

- Name is required, nonblank, trimmed, and limited to 120 characters.
- At least one exercise and one set per exercise are required.
- Positions are nonnegative integers, unique within each parent. Use zero-based
  positions; gaps are accepted. Responses order exercises and sets by position.
- Set type is `warmup` or `working`; target repetitions are positive integers.
- Target weight is optional/null or a nonnegative decimal with at most 8 digits
  total and 2 decimal places. Null means no external-load target.
- Description and exercise notes are optional/null strings.
- Exercises must be system-owned or belong to the authenticated user.

Ownership comes from the access token. No request-body user ID is required.
Template, exercise, and set creation is one atomic transaction.

## Responses and listing

Create returns 201. Detail (`GET /workout-templates/{template_id}`) and PATCH
return 200. All three return `WorkoutTemplateRead`: `id`, `name`, nullable
`description`, `exercises`, `created_at`, and `updated_at`.

Each template exercise contains its own `id`, catalog `exercise_id`, `position`,
`notes`, the nested catalog `exercise`, and `sets`. Each set contains an `id`,
position, set type, target reps, and target weight. Decimal weights are JSON
strings such as `"42.50"`, or null. Template-exercise IDs differ from catalog IDs.

`GET /workout-templates` returns an array of complete owned templates, newest
creation time first with ID as a tie-breaker. An empty list is `[]`.
Pagination is not implemented.

## PATCH semantics

Send only changed fields to `/workout-templates/{template_id}`:

```json
{"name": "Upper body"}
```

| Field | Omitted | Explicit null | Supplied value |
| --- | --- | --- | --- |
| `name` | Keep existing | 422 | Replace validated name |
| `description` | Keep existing | Clear description | Replace description |
| `exercises` | Keep existing | 422 | Replace all exercises and sets |

An empty PATCH object is rejected. To clear the description, send:

```json
{"description": null}
```

When sending `exercises`, include every exercise and set you want to retain,
using the create input shape. Old template exercises/sets are deleted and new
rows receive new IDs. This does not edit catalog exercises. Empty exercise/set
lists are rejected. Replacement and metadata changes commit together; errors
roll back the operation.

## DELETE and errors

`DELETE /workout-templates/{template_id}` returns 204 with no response body.
Nested template exercises/sets are deleted; catalog exercises remain.
Repeating the deletion returns 404.

| Status | Meaning |
| --- | --- |
| 401 | Missing, invalid, or expired authentication |
| 404 | Template missing or owned by someone else |
| 409 | Registration conflicts with an existing account |
| 422 | Invalid input/UUID, unknown muscle-group codes, or unavailable exercises |

Template ownership failures and missing templates both return:

```json
{"detail": "Workout template not found"}
```

Unavailable exercises produce `{"detail": "Unavailable exercises: <uuid>"}`;
multiple IDs are comma-separated. Foreign and missing exercises use the same
error. Pydantic validation instead returns an array in `detail` with field
locations and messages. Clients must handle both string and array forms.

## Manual smoke test

1. Register/login and authorize in `/docs`.
2. Read muscle groups/exercises; create a personal exercise if needed.
3. Create a template with real exercise IDs, list it, and fetch it by ID.
4. PATCH its name and verify other fields remain unchanged.
5. Clear the description, then replace the exercises with a complete list.
6. Delete the template; verify 204 and then 404 on GET.

Automated tests in `tests/test_workout_template_api.py` also cover invalid
authentication, cross-user access, and rejected writes. Workout sessions,
completed sets, history, and progress are not implemented yet.

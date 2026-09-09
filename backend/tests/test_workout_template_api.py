from uuid import uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    MuscleGroup,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from app.services import auth as auth_service
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def fast_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "hash_password", lambda password: "test-hash")
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda plain, hashed: plain == "strong-password" and hashed == "test-hash",
    )


async def login(client: AsyncClient, name: str) -> dict[str, str]:
    registered = await client.post(
        "/auth/register",
        json={
            "email": f"{name}@example.com",
            "username": name,
            "first_name": "Template",
            "last_name": "Tester",
            "password": "strong-password",
        },
    )
    assert registered.is_success, registered.text
    response = await client.post(
        "/auth/login",
        json={"login": f"{name}@example.com", "password": "strong-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def headers(api_client: AsyncClient) -> dict[str, str]:
    return await login(api_client, "owner")


@pytest_asyncio.fixture
async def payload(db_session: AsyncSession) -> dict:
    exercise = Exercise(
        code="bench",
        names={"en": "Bench"},
        muscle_groups=[MuscleGroup(code="chest", names={"en": "Chest"})],
    )
    db_session.add(exercise)
    await db_session.commit()
    return {
        "name": "  Push day  ",
        "description": "Original",
        "exercises": [
            {
                "exercise_id": str(exercise.id),
                "position": 0,
                "sets": [
                    {
                        "position": 1,
                        "set_type": "working",
                        "target_reps": 8,
                        "target_weight_kg": "42.50",
                    },
                    {"position": 0, "set_type": "warmup", "target_reps": 10},
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_template_crud(
    api_client: AsyncClient, db_session: AsyncSession, headers: dict, payload: dict
) -> None:
    empty = await api_client.get("/workout-templates", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []
    created = await api_client.post("/workout-templates", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Push day"
    assert [item["position"] for item in body["exercises"][0]["sets"]] == [0, 1]
    assert body["exercises"][0]["exercise"]["muscle_groups"][0]["code"] == "chest"
    assert body["exercises"][0]["sets"][1]["target_weight_kg"] == "42.50"
    path = f"/workout-templates/{body['id']}"
    fetched = await api_client.get(path, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body
    listed = await api_client.get("/workout-templates", headers=headers)
    assert listed.json() == [body]
    renamed = await api_client.patch(path, headers=headers, json={"name": "New name"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "New name"
    assert renamed.json()["description"] == "Original"
    assert renamed.json()["exercises"] == body["exercises"]
    cleared = await api_client.patch(path, headers=headers, json={"description": None})
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["name"] == "New name"
    replacement = payload["exercises"]
    replacement[0]["sets"] = [{"position": 0, "set_type": "working", "target_reps": 3}]
    updated = await api_client.patch(
        path, headers=headers, json={"exercises": replacement}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["exercises"][0]["id"] != body["exercises"][0]["id"]
    assert updated.json()["exercises"][0]["sets"][0]["target_reps"] == 3
    assert len(updated.json()["exercises"][0]["sets"]) == 1
    deleted = await api_client.delete(path, headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (await api_client.get(path, headers=headers)).status_code == 404
    for model in (WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0
    assert await db_session.scalar(select(func.count()).select_from(Exercise)) == 1


@pytest.mark.parametrize(
    "method,suffix",
    [("GET", ""), ("POST", ""), ("GET", "/id"), ("PATCH", "/id"), ("DELETE", "/id")],
)
@pytest.mark.parametrize("invalid_token", [False, True])
@pytest.mark.asyncio
async def test_endpoints_require_valid_auth(
    api_client: AsyncClient,
    payload: dict,
    method: str,
    suffix: str,
    invalid_token: bool,
) -> None:
    path = "/workout-templates" + (f"/{uuid4()}" if suffix else "")
    response = await api_client.request(
        method,
        path,
        json=payload,
        headers={"Authorization": "Bearer invalid"} if invalid_token else {},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("target", ["foreign", "missing"])
@pytest.mark.asyncio
async def test_other_users_template_is_hidden(
    api_client: AsyncClient, headers: dict, payload: dict, method: str, target: str
) -> None:
    created = await api_client.post("/workout-templates", headers=headers, json=payload)
    assert created.status_code == 201
    body = created.json()
    other = await login(api_client, "other")
    listed = await api_client.get("/workout-templates", headers=other)
    assert listed.json() == []
    template_id = body["id"] if target == "foreign" else str(uuid4())
    response = await api_client.request(
        method,
        f"/workout-templates/{template_id}",
        headers=other,
        json={"name": "Changed"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Workout template not found"}
    original = await api_client.get(f"/workout-templates/{body['id']}", headers=headers)
    assert original.json() == body


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("target", ["foreign", "missing"])
@pytest.mark.asyncio
async def test_unavailable_exercise_is_422(
    api_client: AsyncClient, headers: dict, payload: dict, method: str, target: str
) -> None:
    created = await api_client.post("/workout-templates", headers=headers, json=payload)
    assert created.status_code == 201
    before = created.json()
    bad_id = str(uuid4())
    if target == "foreign":
        other = await login(api_client, "other")
        exercise = await api_client.post(
            "/exercises",
            headers=other,
            json={"name": "Private", "locale": "en", "muscle_group_codes": ["chest"]},
        )
        assert exercise.status_code == 201, exercise.text
        bad_id = exercise.json()["id"]
    payload["exercises"][0]["exercise_id"] = bad_id
    path = "/workout-templates" + (f"/{before['id']}" if method == "PATCH" else "")
    response = await api_client.request(method, path, headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": f"Unavailable exercises: {bad_id}"}
    listed = await api_client.get("/workout-templates", headers=headers)
    assert listed.json() == [before]


@pytest.mark.parametrize(
    "invalid",
    [{}, {"name": None}, {"name": "   "}, {"exercises": None}, {"exercises": []}],
)
@pytest.mark.asyncio
async def test_invalid_patch_is_422(
    api_client: AsyncClient, headers: dict, payload: dict, invalid: dict
) -> None:
    created = await api_client.post("/workout-templates", headers=headers, json=payload)
    assert created.status_code == 201
    path = f"/workout-templates/{created.json()['id']}"
    response = await api_client.patch(path, headers=headers, json=invalid)
    assert response.status_code == 422
    assert (await api_client.get(path, headers=headers)).json() == created.json()


@pytest.mark.parametrize(
    "invalid",
    [
        "blank",
        "empty_exercises",
        "empty_sets",
        "negative_weight",
        "zero_reps",
        "duplicate_positions",
    ],
)
@pytest.mark.asyncio
async def test_invalid_create_is_422(
    api_client: AsyncClient, headers: dict, payload: dict, invalid: str
) -> None:
    if invalid == "blank":
        payload["name"] = "   "
    elif invalid == "empty_exercises":
        payload["exercises"] = []
    elif invalid == "empty_sets":
        payload["exercises"][0]["sets"] = []
    elif invalid == "negative_weight":
        payload["exercises"][0]["sets"][0]["target_weight_kg"] = "-1"
    elif invalid == "zero_reps":
        payload["exercises"][0]["sets"][0]["target_reps"] = 0
    else:
        payload["exercises"][0]["sets"][0]["position"] = 0
    response = await api_client.post(
        "/workout-templates", headers=headers, json=payload
    )
    assert response.status_code == 422
    assert (await api_client.get("/workout-templates", headers=headers)).json() == []


@pytest.mark.asyncio
async def test_invalid_template_uuid_is_422(
    api_client: AsyncClient, headers: dict
) -> None:
    response = await api_client.get("/workout-templates/not-a-uuid", headers=headers)
    assert response.status_code == 422

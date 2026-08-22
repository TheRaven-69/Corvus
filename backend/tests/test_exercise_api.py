import pytest
from app.db.models import Exercise, MuscleGroup
from app.services import auth as auth_service
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def use_fast_password_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed-password",
    )
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda plain_password, password_hash: (
            plain_password == "strong-password" and password_hash == "hashed-password"
        ),
    )


async def authenticated_headers(
    api_client: AsyncClient,
) -> dict[str, str]:
    await api_client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "username": "owner",
            "first_name": "Exercise",
            "last_name": "Owner",
            "password": "strong-password",
        },
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "owner@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


@pytest.mark.asyncio
async def test_get_muscle_groups_returns_catalog(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            MuscleGroup(
                code="triceps",
                names={"en": "Triceps", "uk": "Трицепс"},
            ),
            MuscleGroup(
                code="chest",
                names={"en": "Chest", "uk": "Груди"},
            ),
        ]
    )
    await db_session.commit()

    headers = await authenticated_headers(api_client)

    response = await api_client.get(
        "/muscle-groups",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "code": "chest",
            "names": {"en": "Chest", "uk": "Груди"},
        },
        {
            "code": "triceps",
            "names": {"en": "Triceps", "uk": "Трицепс"},
        },
    ]


@pytest.mark.asyncio
async def test_create_exercise_returns_and_persists_exercise(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            MuscleGroup(
                code="chest",
                names={"en": "Chest", "uk": "Груди"},
            ),
            MuscleGroup(
                code="triceps",
                names={"en": "Triceps", "uk": "Трицепс"},
            ),
        ]
    )
    await db_session.commit()

    headers = await authenticated_headers(api_client)

    response = await api_client.post(
        "/exercises",
        headers=headers,
        json={
            "name": "  Жим гантелей  ",
            "locale": "uk",
            "muscle_group_codes": ["triceps", "chest"],
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["code"] is None
    assert body["names"] == {
        "uk": "Жим гантелей",
    }
    assert [group["code"] for group in body["muscle_groups"]] == ["chest", "triceps"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body

    stored_exercise = (
        await db_session.scalars(
            select(Exercise),
        )
    ).one()

    assert str(stored_exercise.id) == body["id"]
    assert stored_exercise.names == {
        "uk": "Жим гантелей",
    }


@pytest.mark.asyncio
async def test_create_exercise_rejects_unknown_muscle_groups(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add(
        MuscleGroup(
            code="chest",
            names={"en": "Chest", "uk": "Груди"},
        )
    )
    await db_session.commit()

    headers = await authenticated_headers(api_client)

    response = await api_client.post(
        "/exercises",
        headers=headers,
        json={
            "name": "Політ",
            "locale": "uk",
            "muscle_group_codes": ["chest", "wings"],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unknown muscle groups: wings",
    }

    stored_exercises = (
        await db_session.scalars(
            select(Exercise),
        )
    ).all()

    assert stored_exercises == []


@pytest.mark.asyncio
async def test_exercise_endpoints_require_authentication(
    api_client: AsyncClient,
) -> None:
    responses = [
        await api_client.get("/muscle-groups"),
        await api_client.get("/exercises"),
        await api_client.post(
            "/exercises",
            json={
                "name": "Жим гантелей",
                "locale": "uk",
                "muscle_group_codes": ["chest"],
            },
        ),
    ]

    for response in responses:
        assert response.status_code == 401, (
            response.request.method,
            response.request.url.path,
            response.status_code,
            response.text,
        )

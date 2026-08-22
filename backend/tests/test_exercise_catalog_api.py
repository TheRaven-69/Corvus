import pytest
from app.db.models import Exercise, MuscleGroup, User
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

    return {
        "Authorization": (f"Bearer {login_response.json()['access_token']}"),
    }


@pytest.mark.asyncio
async def test_get_exercises_returns_empty_catalog(
    api_client: AsyncClient,
) -> None:
    headers = await authenticated_headers(api_client)

    response = await api_client.get("/exercises", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_exercises_returns_system_and_owned_exercises_only(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await authenticated_headers(api_client)
    current_user = (
        await db_session.scalars(select(User).where(User.email == "owner@example.com"))
    ).one()
    other_user = User(
        email="other@example.com",
        username="other",
        first_name="Other",
        last_name="User",
        password_hash="not-a-real-hash",
    )
    chest = MuscleGroup(
        code="chest",
        names={"en": "Chest", "uk": "Груди"},
    )
    system_exercise = Exercise(
        code="barbell_bench_press",
        names={
            "en": "Barbell bench press",
            "uk": "Жим штанги лежачи",
        },
        muscle_groups=[chest],
    )
    own_exercise = Exercise(
        owner=current_user,
        code=None,
        names={"uk": "Моя вправа"},
        muscle_groups=[chest],
    )
    other_users_exercise = Exercise(
        owner=other_user,
        code=None,
        names={"uk": "Чужа вправа"},
        muscle_groups=[chest],
    )

    db_session.add_all(
        [
            other_user,
            chest,
            system_exercise,
            own_exercise,
            other_users_exercise,
        ]
    )
    await db_session.commit()

    response = await api_client.get("/exercises", headers=headers)

    assert response.status_code == 200
    response_ids = {exercise["id"] for exercise in response.json()}
    assert response_ids == {
        str(system_exercise.id),
        str(own_exercise.id),
    }
    assert str(other_users_exercise.id) not in response_ids


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "   ",
            "locale": "uk",
            "muscle_group_codes": ["chest"],
        },
        {
            "name": "Bench press",
            "locale": "de",
            "muscle_group_codes": ["chest"],
        },
        {
            "name": "Жим лежачи",
            "locale": "uk",
            "muscle_group_codes": [],
        },
        {
            "name": "Жим лежачи",
            "locale": "uk",
            "muscle_group_codes": ["chest", "chest"],
        },
    ],
)
@pytest.mark.asyncio
async def test_create_exercise_rejects_invalid_payload(
    api_client: AsyncClient,
    payload: dict[str, object],
) -> None:
    headers = await authenticated_headers(api_client)

    response = await api_client.post(
        "/exercises",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422

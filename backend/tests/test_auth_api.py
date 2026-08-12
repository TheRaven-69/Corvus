from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models import AuthSession
from app.services import auth as auth_service
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def valid_registration_data() -> dict[str, str]:
    return {
        "email": "vadim@example.com",
        "username": "vadim",
        "first_name": "Vadim",
        "last_name": "Test",
        "password": "strong-password",
    }


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


@pytest.mark.asyncio
async def test_register_returns_created_user(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["email"] == "vadim@example.com"
    assert body["username"] == "vadim"
    assert body["first_name"] == "Vadim"
    assert body["last_name"] == "Test"
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(
    api_client: AsyncClient,
) -> None:
    first_response = await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )

    second_data = valid_registration_data()
    second_data["email"] = "VADIM@example.com"
    second_data["username"] = "another_user"

    second_response = await api_client.post(
        "/auth/register",
        json=second_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Email is already registered",
    }


@pytest.mark.asyncio
async def test_register_rejects_duplicate_username(
    api_client: AsyncClient,
) -> None:
    first_response = await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )

    second_data = valid_registration_data()
    second_data["email"] = "another@example.com"
    second_data["username"] = "VADIM"

    second_response = await api_client.post(
        "/auth/register",
        json=second_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Username is already registered",
    }


@pytest.mark.asyncio
async def test_register_rejects_invalid_request(
    api_client: AsyncClient,
) -> None:
    data = valid_registration_data()
    data["email"] = "not-an-email"
    data["password"] = "short"

    response = await api_client.post(
        "/auth/register",
        json=data,
    )

    assert response.status_code == 422

    error_locations = {tuple(error["loc"]) for error in response.json()["detail"]}

    assert ("body", "email") in error_locations
    assert ("body", "password") in error_locations


@pytest.mark.parametrize(
    "login",
    ["VADIM@EXAMPLE.COM", "VADIM"],
)
@pytest.mark.asyncio
async def test_login_returns_access_token_and_refresh_cookie(
    api_client: AsyncClient,
    login: str,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )

    response = await api_client.post(
        "/auth/login",
        json={
            "login": login,
            "password": "strong-password",
        },
    )

    assert response.status_code == 200

    body = response.json()
    set_cookie = response.headers["set-cookie"]

    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    assert response.cookies.get("refresh_token")
    assert "HttpOnly" in set_cookie
    assert "Path=/auth" in set_cookie
    assert "SameSite=lax" in set_cookie


@pytest.mark.parametrize(
    ("login", "password"),
    [
        ("unknown@example.com", "strong-password"),
        ("vadim@example.com", "wrong-password"),
    ],
)
@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(
    api_client: AsyncClient,
    login: str,
    password: str,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )

    response = await api_client.post(
        "/auth/login",
        json={
            "login": login,
            "password": password,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}
    assert "refresh_token" not in response.cookies


@pytest.mark.asyncio
async def test_login_rejects_missing_credentials(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/auth/login",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_rotates_cookie_and_returns_access_token(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "vadim@example.com",
            "password": "strong-password",
        },
    )
    original_refresh_token = login_response.cookies["refresh_token"]
    original_access_payload = decode_access_token(
        login_response.json()["access_token"],
    )

    refresh_response = await api_client.post("/auth/refresh")

    assert refresh_response.status_code == 200

    body = refresh_response.json()
    refreshed_access_payload = decode_access_token(body["access_token"])
    rotated_refresh_token = refresh_response.cookies["refresh_token"]

    assert body["token_type"] == "bearer"
    assert rotated_refresh_token != original_refresh_token
    assert refreshed_access_payload["sub"] == original_access_payload["sub"]
    assert refreshed_access_payload["sid"] == original_access_payload["sid"]
    assert "HttpOnly" in refresh_response.headers["set-cookie"]

    api_client.cookies.clear()
    replay_response = await api_client.post(
        "/auth/refresh",
        headers={
            "Cookie": f"refresh_token={original_refresh_token}",
        },
    )

    assert replay_response.status_code == 401
    assert replay_response.json() == {
        "detail": "Invalid refresh token",
    }


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Cookie": "refresh_token=unknown-refresh-token"},
    ],
)
@pytest.mark.asyncio
async def test_refresh_rejects_missing_or_unknown_cookie(
    api_client: AsyncClient,
    headers: dict[str, str],
) -> None:
    response = await api_client.post(
        "/auth/refresh",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid refresh token",
    }


@pytest.mark.asyncio
async def test_me_returns_authenticated_user(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "vadim@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]

    response = await api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["email"] == "vadim@example.com"
    assert body["username"] == "vadim"
    assert body["first_name"] == "Vadim"
    assert body["last_name"] == "Test"
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_me_rejects_missing_access_token(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_me_rejects_malformed_access_token(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_me_rejects_expired_access_token(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "vadim@example.com",
            "password": "strong-password",
        },
    )
    valid_payload = decode_access_token(
        login_response.json()["access_token"],
    )
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": valid_payload["sub"],
            "sid": valid_payload["sid"],
            "type": "access",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    response = await api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token"}


@pytest.mark.asyncio
async def test_me_rejects_access_token_from_revoked_session(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "vadim@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]
    access_payload = decode_access_token(access_token)
    auth_session = await db_session.scalar(
        select(AuthSession).where(
            AuthSession.id == UUID(str(access_payload["sid"])),
        )
    )
    assert auth_session is not None

    auth_session.revoked_at = datetime.now(UTC)
    await db_session.commit()

    response = await api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token"}


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/auth/register",
        json=valid_registration_data(),
    )
    login_response = await api_client.post(
        "/auth/login",
        json={
            "login": "vadim@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.cookies["refresh_token"]

    response = await api_client.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    assert api_client.cookies.get("refresh_token") is None

    set_cookie = response.headers["set-cookie"]

    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "Path=/auth" in set_cookie

    refresh_response = await api_client.post(
        "/auth/refresh",
        headers={
            "Cookie": f"refresh_token={refresh_token}",
        },
    )
    me_response = await api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json() == {
        "detail": "Invalid refresh token",
    }
    assert me_response.status_code == 401
    assert me_response.json() == {"detail": "Invalid access token"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Cookie": "refresh_token=unknown-refresh-token"},
    ],
)
@pytest.mark.asyncio
async def test_logout_is_idempotent_without_valid_cookie(
    api_client: AsyncClient,
    headers: dict[str, str],
) -> None:
    response = await api_client.post(
        "/auth/logout",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert "Max-Age=0" in response.headers["set-cookie"]

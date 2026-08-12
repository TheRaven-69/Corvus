from datetime import UTC, datetime, timedelta

import pytest
from app.core.security import decode_access_token, hash_refresh_token
from app.db.models import AuthSession
from app.repositories import user as user_repository
from app.schemas.auth import LoginRequest
from app.schemas.user import UserRegister
from app.services import auth as auth_service
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UsernameAlreadyExistsError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_authenticated_session(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> auth_service.TokenPair:
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

    await auth_service.register_user(
        db_session,
        UserRegister(
            email="vadim@example.com",
            username="vadim",
            first_name="Vadim",
            last_name="Test",
            password="strong-password",
        ),
    )

    return await auth_service.login_user(
        db_session,
        LoginRequest(
            login="vadim@example.com",
            password="strong-password",
        ),
    )


@pytest.mark.asyncio
async def test_register_user_creates_normalized_user(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = UserRegister(
        email="Vadim@Example.com",
        username="Vadim_123",
        first_name=" Vadim ",
        last_name=" Test ",
        password="strong-password",
    )

    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed-password",
    )

    created_user = await auth_service.register_user(
        db_session,
        data,
    )

    stored_user = await user_repository.get_user_by_email(
        db_session,
        "vadim@example.com",
    )

    assert stored_user is not None
    assert stored_user.id == created_user.id
    assert stored_user.email == "vadim@example.com"
    assert stored_user.username == "vadim_123"
    assert stored_user.first_name == "Vadim"
    assert stored_user.last_name == "Test"
    assert stored_user.password_hash == "hashed-password"
    assert stored_user.password_hash != data.password


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_email(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed-password",
    )

    first_user = UserRegister(
        email="vadim@example.com",
        username="vadim",
        first_name="Vadim",
        last_name="Test",
        password="strong-password",
    )
    second_user = UserRegister(
        email="VADIM@example.com",
        username="another_user",
        first_name="Another",
        last_name="User",
        password="another-password",
    )

    await auth_service.register_user(db_session, first_user)

    with pytest.raises(EmailAlreadyExistsError):
        await auth_service.register_user(
            db_session,
            second_user,
        )


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_username(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda password: "hashed-password",
    )

    first_user = UserRegister(
        email="first@example.com",
        username="vadim",
        first_name="Vadim",
        last_name="Test",
        password="strong-password",
    )
    second_user = UserRegister(
        email="second@example.com",
        username="VADIM",
        first_name="Another",
        last_name="User",
        password="another-password",
    )

    await auth_service.register_user(db_session, first_user)

    with pytest.raises(UsernameAlreadyExistsError):
        await auth_service.register_user(
            db_session,
            second_user,
        )


@pytest.mark.asyncio
async def test_login_user_creates_auth_session_and_tokens(
    db_session: AsyncSession,
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

    user = await auth_service.register_user(
        db_session,
        UserRegister(
            email="vadim@example.com",
            username="vadim",
            first_name="Vadim",
            last_name="Test",
            password="strong-password",
        ),
    )

    result = await auth_service.login_user(
        db_session,
        LoginRequest(
            login=" VADIM@EXAMPLE.COM ",
            password="strong-password",
        ),
    )

    auth_session = (await db_session.scalars(select(AuthSession))).one()
    access_payload = decode_access_token(result.access_token)

    assert auth_session.user_id == user.id
    assert auth_session.refresh_token_hash == hash_refresh_token(result.refresh_token)
    assert auth_session.refresh_token_hash != result.refresh_token
    assert auth_session.revoked_at is None
    assert access_payload["sub"] == str(user.id)
    assert access_payload["sid"] == str(auth_session.id)
    assert access_payload["type"] == "access"


@pytest.mark.parametrize(
    ("login", "password"),
    [
        ("unknown@example.com", "strong-password"),
        ("vadim@example.com", "wrong-password"),
    ],
)
@pytest.mark.asyncio
async def test_login_user_rejects_invalid_credentials_without_session(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    login: str,
    password: str,
) -> None:
    monkeypatch.setattr(
        auth_service,
        "hash_password",
        lambda raw_password: "hashed-password",
    )
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda plain_password, password_hash: (
            plain_password == "strong-password" and password_hash == "hashed-password"
        ),
    )

    await auth_service.register_user(
        db_session,
        UserRegister(
            email="vadim@example.com",
            username="vadim",
            first_name="Vadim",
            last_name="Test",
            password="strong-password",
        ),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login_user(
            db_session,
            LoginRequest(
                login=login,
                password=password,
            ),
        )

    auth_session = (await db_session.scalars(select(AuthSession))).one_or_none()

    assert auth_session is None


@pytest.mark.asyncio
async def test_refresh_tokens_rotates_token_and_preserves_session(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    login_result = await create_authenticated_session(
        db_session,
        monkeypatch,
    )
    original_access_payload = decode_access_token(
        login_result.access_token,
    )

    refresh_result = await auth_service.refresh_tokens(
        db_session,
        login_result.refresh_token,
    )

    auth_session = (await db_session.scalars(select(AuthSession))).one()
    refreshed_access_payload = decode_access_token(
        refresh_result.access_token,
    )

    assert refresh_result.refresh_token != login_result.refresh_token
    assert auth_session.refresh_token_hash == hash_refresh_token(
        refresh_result.refresh_token
    )
    assert auth_session.refresh_token_hash != hash_refresh_token(
        login_result.refresh_token
    )
    assert refreshed_access_payload["sub"] == original_access_payload["sub"]
    assert refreshed_access_payload["sid"] == original_access_payload["sid"]
    assert refreshed_access_payload["sid"] == str(auth_session.id)


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_rotated_token(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    login_result = await create_authenticated_session(
        db_session,
        monkeypatch,
    )

    refresh_result = await auth_service.refresh_tokens(
        db_session,
        login_result.refresh_token,
    )

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh_tokens(
            db_session,
            login_result.refresh_token,
        )

    second_refresh_result = await auth_service.refresh_tokens(
        db_session,
        refresh_result.refresh_token,
    )

    assert second_refresh_result.refresh_token != refresh_result.refresh_token


@pytest.mark.asyncio
async def test_logout_user_revokes_auth_session(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    login_result = await create_authenticated_session(
        db_session,
        monkeypatch,
    )

    await auth_service.logout_user(
        db_session,
        login_result.refresh_token,
    )

    auth_session = (await db_session.scalars(select(AuthSession))).one()

    assert auth_session.revoked_at is not None

    await db_session.rollback()

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh_tokens(
            db_session,
            login_result.refresh_token,
        )

    with pytest.raises(InvalidAccessTokenError):
        await auth_service.authenticate_access_token(
            db_session,
            login_result.access_token,
        )


@pytest.mark.parametrize(
    "refresh_token",
    [None, "unknown-refresh-token"],
)
@pytest.mark.asyncio
async def test_refresh_tokens_rejects_missing_or_unknown_token(
    db_session: AsyncSession,
    refresh_token: str | None,
) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh_tokens(
            db_session,
            refresh_token,
        )


@pytest.mark.parametrize(
    "invalid_state",
    ["expired", "revoked"],
)
@pytest.mark.asyncio
async def test_refresh_tokens_rejects_inactive_session(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    invalid_state: str,
) -> None:
    login_result = await create_authenticated_session(
        db_session,
        monkeypatch,
    )
    auth_session = (await db_session.scalars(select(AuthSession))).one()

    if invalid_state == "expired":
        auth_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    else:
        auth_session.revoked_at = datetime.now(UTC)

    await db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh_tokens(
            db_session,
            login_result.refresh_token,
        )

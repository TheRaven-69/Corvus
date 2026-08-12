from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from jwt.exceptions import InvalidTokenError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import User
from app.repositories import auth_session as auth_session_repository
from app.repositories import user as user_repository
from app.schemas.auth import LoginRequest
from app.schemas.user import UserRegister
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
    UsernameAlreadyExistsError,
)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


async def login_user(
    session: AsyncSession,
    data: LoginRequest,
) -> TokenPair:
    login = data.login.strip().casefold()

    async with session.begin():
        user = await user_repository.get_user_by_login(
            session,
            login,
        )

        if user is None or not verify_password(
            data.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError

        refresh_token = generate_refresh_token()

        auth_session = await auth_session_repository.create_auth_session(
            session,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )

        access_token = create_access_token(
            user_id=user.id,
            session_id=auth_session.id,
        )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str | None,
) -> TokenPair:
    if not refresh_token:
        raise InvalidRefreshTokenError

    now = datetime.now(UTC)
    current_token_hash = hash_refresh_token(refresh_token)

    async with session.begin():
        auth_session = (
            await auth_session_repository.get_auth_session_by_refresh_token_hash(
                session,
                current_token_hash,
            )
        )

        if auth_session is None:
            raise InvalidRefreshTokenError

        expires_at = auth_session.expires_at

        # SQLite may return timezone-naive values.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if auth_session.revoked_at is not None or expires_at <= now:
            raise InvalidRefreshTokenError

        new_refresh_token = generate_refresh_token()
        new_expires_at = now + timedelta(
            days=settings.refresh_token_expire_days,
        )

        await auth_session_repository.rotate_auth_session_refresh_token(
            session,
            auth_session,
            refresh_token_hash=hash_refresh_token(
                new_refresh_token,
            ),
            expires_at=new_expires_at,
        )

        access_token = create_access_token(
            user_id=auth_session.user_id,
            session_id=auth_session.id,
        )

    return TokenPair(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


async def register_user(
    session: AsyncSession,
    data: UserRegister,
) -> User:
    email = str(data.email).casefold()
    username = data.username.casefold()
    password_hash = hash_password(data.password)

    try:
        async with session.begin():
            existing_email = await user_repository.get_user_by_email(
                session,
                email,
            )
            if existing_email is not None:
                raise EmailAlreadyExistsError

            existing_username = await user_repository.get_user_by_username(
                session,
                username,
            )
            if existing_username is not None:
                raise UsernameAlreadyExistsError

            return await user_repository.create_user(
                session,
                email=email,
                username=username,
                first_name=data.first_name.strip(),
                last_name=data.last_name.strip(),
                password_hash=password_hash,
            )
    except IntegrityError as error:
        raise UserAlreadyExistsError from error


async def authenticate_access_token(
    session: AsyncSession,
    access_token: str,
) -> User:
    try:
        payload = decode_access_token(access_token)

        user_id = UUID(str(payload["sub"]))
        auth_session_id = UUID(str(payload["sid"]))
    except (
        InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise InvalidAccessTokenError from error

    auth_session = await auth_session_repository.get_auth_session_by_id(
        session,
        auth_session_id,
    )

    if (
        auth_session is None
        or auth_session.user_id != user_id
        or auth_session.revoked_at is not None
        or as_utc(auth_session.expires_at) <= datetime.now(UTC)
    ):
        raise InvalidAccessTokenError

    user = await user_repository.get_user_by_id(
        session,
        user_id,
    )

    if user is None:
        raise InvalidAccessTokenError

    return user


async def logout_user(
    session: AsyncSession,
    refresh_token: str | None,
) -> None:
    if not refresh_token:
        return

    refresh_token_hash = hash_refresh_token(refresh_token)

    async with session.begin():
        auth_session = (
            await auth_session_repository.get_auth_session_by_refresh_token_hash(
                session,
                refresh_token_hash,
            )
        )

        if auth_session is None or auth_session.revoked_at is not None:
            return

        await auth_session_repository.revoke_auth_session(
            session, auth_session, revoked_at=datetime.now(UTC)
        )

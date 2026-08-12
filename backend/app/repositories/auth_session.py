from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthSession


async def create_auth_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    refresh_token_hash: str,
    expires_at: datetime,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
    )
    session.add(auth_session)
    await session.flush()

    return auth_session


async def get_auth_session_by_refresh_token_hash(
    session: AsyncSession,
    refresh_token_hash: str,
) -> AuthSession | None:
    statement = (
        select(AuthSession)
        .where(
            AuthSession.refresh_token_hash == refresh_token_hash,
        )
        .with_for_update()
    )

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def rotate_auth_session_refresh_token(
    session: AsyncSession,
    auth_session: AuthSession,
    *,
    refresh_token_hash: str,
    expires_at: datetime,
) -> AuthSession:
    auth_session.refresh_token_hash = refresh_token_hash
    auth_session.expires_at = expires_at

    await session.flush()

    return auth_session


async def get_auth_session_by_id(
    session: AsyncSession,
    auth_session_id: UUID,
) -> AuthSession | None:
    statement = select(AuthSession).where(
        AuthSession.id == auth_session_id,
    )
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def revoke_auth_session(
    session: AsyncSession,
    auth_session: AuthSession,
    *,
    revoked_at: datetime,
) -> None:
    auth_session.revoked_at = revoked_at

    await session.flush()

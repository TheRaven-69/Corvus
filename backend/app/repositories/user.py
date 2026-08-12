from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> User | None:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_user_by_username(
    session: AsyncSession,
    username: str,
) -> User | None:
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    username: str,
    first_name: str,
    last_name: str,
    password_hash: str,
) -> User:
    user = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        password_hash=password_hash,
    )

    session.add(user)
    await session.flush()

    return user


async def get_user_by_login(
    session: AsyncSession,
    login: str,
) -> User | None:
    statement = select(User).where(
        or_(
            User.email == login,
            User.username == login,
        )
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: UUID,
) -> User | None:
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)

    return result.scalar_one_or_none()

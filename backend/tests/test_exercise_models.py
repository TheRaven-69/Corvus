import pytest
from app.db.models import Exercise, User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_system_exercise_requires_code(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Exercise(
            owner_user_id=None,
            code=None,
            names={"en": "Invalid system exercise"},
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_custom_exercise_cannot_have_system_code(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="owner@example.com",
        username="owner",
        first_name="Exercise",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )
    db_session.add(user)
    await db_session.commit()

    db_session.add(
        Exercise(
            owner_user_id=user.id,
            code="invalid_custom_system_mix",
            names={"en": "Invalid custom exercise"},
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exercise, MuscleGroup


async def list_muscle_groups(
    session: AsyncSession,
) -> list[MuscleGroup]:
    statement = select(MuscleGroup).order_by(
        MuscleGroup.code,
    )
    result = await session.execute(statement)

    return list(result.scalars())


async def get_muscle_groups_by_codes(
    session: AsyncSession,
    codes: list[str],
) -> list[MuscleGroup]:
    statement = (
        select(MuscleGroup)
        .where(MuscleGroup.code.in_(codes))
        .order_by(MuscleGroup.code)
    )
    result = await session.execute(statement)

    return list(result.scalars())


async def create_custom_exercise(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    names: dict[str, str],
    muscle_groups: list[MuscleGroup],
) -> Exercise:
    exercise = Exercise(
        owner_user_id=owner_user_id,
        code=None,
        names=names,
        muscle_groups=muscle_groups,
    )

    session.add(exercise)
    await session.flush()

    return exercise


async def list_visible_exercises(
    session: AsyncSession,
    user_id: UUID,
) -> list[Exercise]:
    statement = (
        select(Exercise)
        .where(
            or_(
                Exercise.owner_user_id.is_(None),
                Exercise.owner_user_id == user_id,
            )
        )
        .order_by(
            Exercise.created_at,
            Exercise.id,
        )
    )
    result = await session.execute(statement)

    return list(result.scalars())

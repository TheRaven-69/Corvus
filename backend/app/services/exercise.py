from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exercise, MuscleGroup
from app.repositories import exercise as exercise_repository
from app.schemas.exercise import ExerciseCreate
from app.services.exceptions import UnknownMuscleGroupsError


async def list_muscle_groups(
    session: AsyncSession,
) -> list[MuscleGroup]:
    return await exercise_repository.list_muscle_groups(session)


async def list_visible_exercises(
    session: AsyncSession,
    user_id: UUID,
) -> list[Exercise]:
    return await exercise_repository.list_visible_exercises(
        session,
        user_id,
    )


async def create_custom_exercise(
    session: AsyncSession,
    *,
    user_id: UUID,
    data: ExerciseCreate,
) -> Exercise:
    try:
        muscle_groups = await exercise_repository.get_muscle_groups_by_codes(
            session,
            data.muscle_group_codes,
        )

        found_codes = {muscle_group.code for muscle_group in muscle_groups}
        unknown_codes = [
            code for code in data.muscle_group_codes if code not in found_codes
        ]

        if unknown_codes:
            raise UnknownMuscleGroupsError(unknown_codes)

        exercise = await exercise_repository.create_custom_exercise(
            session,
            owner_user_id=user_id,
            names={data.locale: data.name},
            muscle_groups=muscle_groups,
        )

        await session.commit()

        return exercise
    except Exception:
        await session.rollback()
        raise

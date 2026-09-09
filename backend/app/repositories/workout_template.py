from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Exercise, WorkoutTemplate, WorkoutTemplateExercise


async def get_workout_template_by_id(
    session: AsyncSession,
    *,
    template_id: UUID,
    user_id: UUID,
) -> WorkoutTemplate | None:
    statement = (
        select(WorkoutTemplate)
        .where(
            WorkoutTemplate.id == template_id,
            WorkoutTemplate.user_id == user_id,
        )
        .options(
            selectinload(WorkoutTemplate.exercises).selectinload(
                WorkoutTemplateExercise.sets,
            ),
            selectinload(WorkoutTemplate.exercises)
            .selectinload(WorkoutTemplateExercise.exercise)
            .selectinload(Exercise.muscle_groups),
        )
        .execution_options(populate_existing=True)
    )
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def list_workout_templates(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> list[WorkoutTemplate]:
    statement = (
        select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == user_id)
        .options(
            selectinload(WorkoutTemplate.exercises).selectinload(
                WorkoutTemplateExercise.sets,
            ),
            selectinload(WorkoutTemplate.exercises)
            .selectinload(WorkoutTemplateExercise.exercise)
            .selectinload(Exercise.muscle_groups),
        )
        .order_by(
            WorkoutTemplate.created_at.desc(),
            WorkoutTemplate.id,
        )
    )
    result = await session.execute(statement)

    return list(result.scalars())


async def create_workout_template(
    session: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    description: str | None,
    exercises: list[WorkoutTemplateExercise],
) -> WorkoutTemplate:
    template = WorkoutTemplate(
        user_id=user_id,
        name=name,
        description=description,
        exercises=exercises,
    )

    session.add(template)
    await session.flush()

    return template


async def replace_workout_template_exercises(
    session: AsyncSession,
    *,
    template: WorkoutTemplate,
    exercises: list[WorkoutTemplateExercise],
) -> WorkoutTemplate:
    template.exercises.clear()
    await session.flush()

    template.exercises = exercises
    await session.flush()

    return template


async def update_workout_template(
    session: AsyncSession,
    *,
    template: WorkoutTemplate,
    name: str,
    description: str | None,
) -> WorkoutTemplate:
    template.name = name
    template.description = description
    template.updated_at = datetime.now(UTC)

    await session.flush()

    return template


async def delete_workout_template(
    session: AsyncSession,
    *,
    template: WorkoutTemplate,
) -> None:
    await session.delete(template)
    await session.flush()

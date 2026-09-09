from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from app.repositories import exercise as exercise_repository
from app.repositories import workout_template as workout_template_repository
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateExerciseCreate,
    WorkoutTemplateUpdate,
)
from app.services.exceptions import (
    UnavailableExercisesError,
    WorkoutTemplateNotFoundError,
)


async def _validate_exercises_are_visible(
    session: AsyncSession,
    *,
    user_id: UUID,
    exercises: list[WorkoutTemplateExerciseCreate],
) -> None:
    requested_ids = {item.exercise_id for item in exercises}

    visible_exercises = await exercise_repository.get_visible_exercises_by_ids(
        session,
        user_id=user_id,
        exercise_ids=requested_ids,
    )

    found_ids = {exercise.id for exercise in visible_exercises}
    unavailable_ids = requested_ids - found_ids

    if unavailable_ids:
        raise UnavailableExercisesError(unavailable_ids)


def _build_workout_template_exercises(
    exercises: list[WorkoutTemplateExerciseCreate],
) -> list[WorkoutTemplateExercise]:
    template_exercises: list[WorkoutTemplateExercise] = []

    for exercise_data in exercises:
        workout_sets = [
            WorkoutTemplateSet(
                position=set_data.position,
                set_type=set_data.set_type,
                target_reps=set_data.target_reps,
                target_weight_kg=set_data.target_weight_kg,
            )
            for set_data in exercise_data.sets
        ]

        template_exercises.append(
            WorkoutTemplateExercise(
                exercise_id=exercise_data.exercise_id,
                position=exercise_data.position,
                notes=exercise_data.notes,
                sets=workout_sets,
            )
        )

    return template_exercises


async def get_workout_template(
    session: AsyncSession,
    *,
    user_id: UUID,
    template_id: UUID,
) -> WorkoutTemplate:
    template = await workout_template_repository.get_workout_template_by_id(
        session,
        template_id=template_id,
        user_id=user_id,
    )

    if template is None:
        raise WorkoutTemplateNotFoundError

    return template


async def list_workout_templates(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> list[WorkoutTemplate]:
    return await workout_template_repository.list_workout_templates(
        session,
        user_id=user_id,
    )


async def create_workout_template(
    session: AsyncSession,
    *,
    user_id: UUID,
    data: WorkoutTemplateCreate,
) -> WorkoutTemplate:
    try:
        await _validate_exercises_are_visible(
            session,
            user_id=user_id,
            exercises=data.exercises,
        )

        template = await workout_template_repository.create_workout_template(
            session,
            user_id=user_id,
            name=data.name,
            description=data.description,
            exercises=_build_workout_template_exercises(data.exercises),
        )

        saved_template = await get_workout_template(
            session,
            user_id=user_id,
            template_id=template.id,
        )

        await session.commit()

        return saved_template
    except Exception:
        await session.rollback()
        raise


async def update_workout_template(
    session: AsyncSession,
    *,
    user_id: UUID,
    template_id: UUID,
    data: WorkoutTemplateUpdate,
) -> WorkoutTemplate:
    try:
        template = await get_workout_template(
            session,
            user_id=user_id,
            template_id=template_id,
        )

        name = data.name if data.name is not None else template.name
        description = (
            data.description
            if "description" in data.model_fields_set
            else template.description
        )
        if data.exercises is not None:
            await _validate_exercises_are_visible(
                session,
                user_id=user_id,
                exercises=data.exercises,
            )

            await workout_template_repository.replace_workout_template_exercises(
                session,
                template=template,
                exercises=_build_workout_template_exercises(data.exercises),
            )

        await workout_template_repository.update_workout_template(
            session,
            template=template,
            name=name,
            description=description,
        )

        saved_template = await get_workout_template(
            session,
            user_id=user_id,
            template_id=template.id,
        )
        await session.commit()

        return saved_template
    except Exception:
        await session.rollback()
        raise


async def delete_workout_template(
    session: AsyncSession,
    *,
    user_id: UUID,
    template_id: UUID,
) -> None:
    try:
        template = await get_workout_template(
            session,
            user_id=user_id,
            template_id=template_id,
        )

        await workout_template_repository.delete_workout_template(
            session,
            template=template,
        )

        await session.commit()
    except Exception:
        await session.rollback()
        raise

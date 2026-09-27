from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
    WorkoutTemplate,
)
from app.repositories import exercise as exercise_repository
from app.repositories import workout_session as workout_session_repository
from app.repositories import workout_template as workout_template_repository
from app.schemas.workout_session import (
    WorkoutSessionCreate,
    WorkoutSessionExerciseCreate,
    WorkoutSessionExercisesReorder,
    WorkoutSessionExerciseUpdate,
    WorkoutSessionHistoryRead,
    WorkoutSessionSetCreate,
    WorkoutSessionSetUpdate,
    WorkoutSessionStatsRead,
    WorkoutSessionUpdate,
)
from app.services.exceptions import (
    ActiveWorkoutSessionExistsError,
    InvalidWorkoutSessionExerciseOrderError,
    InvalidWorkoutSessionSetError,
    InvalidWorkoutTemplateError,
    UnavailableExercisesError,
    WorkoutSessionCancellationNotAllowedError,
    WorkoutSessionCompletionNotAllowedError,
    WorkoutSessionExerciseDeletionNotAllowedError,
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionExerciseReplacementNotAllowedError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
    WorkoutSessionSetDeletionNotAllowedError,
    WorkoutSessionSetNotFoundError,
    WorkoutTemplateNotFoundError,
)


async def _get_active_session_for_update(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> WorkoutSession:
    workout = await workout_session_repository.get_workout_session_by_id(
        session,
        session_id=session_id,
        user_id=user_id,
        for_update=True,
    )

    if workout is None:
        raise WorkoutSessionNotFoundError()

    if workout.status != "in_progress":
        raise WorkoutSessionNotActiveError()

    return workout


def _find_session_set(
    workout: WorkoutSession,
    *,
    set_id: UUID,
) -> WorkoutSessionSet:
    for exercise in workout.exercises:
        for workout_set in exercise.sets:
            if workout_set.id == set_id:
                return workout_set

    raise WorkoutSessionSetNotFoundError()


def _apply_set_update(
    workout_set: WorkoutSessionSet,
    data: WorkoutSessionSetUpdate,
) -> None:
    changes = data.model_dump(exclude_unset=True)

    next_status = changes.get("status", workout_set.status)
    next_reps = changes.get("actual_reps", workout_set.actual_reps)

    if next_status == "completed" and next_reps is None:
        raise InvalidWorkoutSessionSetError()

    if "actual_reps" in changes:
        workout_set.actual_reps = data.actual_reps

    if "actual_weight_kg" in changes:
        workout_set.actual_weight_kg = data.actual_weight_kg

    if next_status == "completed":
        if workout_set.status != "completed":
            workout_set.completed_at = datetime.now(UTC)

    else:
        workout_set.completed_at = None

    workout_set.status = next_status


async def _get_startable_template(
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
        raise WorkoutTemplateNotFoundError()

    if not template.exercises or any(
        not exercise.sets for exercise in template.exercises
    ):
        raise InvalidWorkoutTemplateError()

    return template


def _build_session_exercises(
    template: WorkoutTemplate,
) -> list[WorkoutSessionExercise]:
    session_exercises: list[WorkoutSessionExercise] = []

    for template_exercise in template.exercises:
        exercise = template_exercise.exercise

        session_sets = [
            WorkoutSessionSet(
                position=template_set.position,
                set_type=template_set.set_type,
                planned_reps=template_set.target_reps,
                planned_weight_kg=template_set.target_weight_kg,
                status="pending",
            )
            for template_set in template_exercise.sets
        ]

        session_exercises.append(
            WorkoutSessionExercise(
                exercise_id=exercise.id,
                position=template_exercise.position,
                exercise_snapshot={
                    "names": dict(exercise.names),
                    "muscle_groups": sorted(
                        group.code for group in exercise.muscle_groups
                    ),
                },
                notes=template_exercise.notes,
                sets=session_sets,
            )
        )

    return session_exercises


async def get_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> WorkoutSession:
    workout = await workout_session_repository.get_workout_session_by_id(
        session,
        session_id=session_id,
        user_id=user_id,
    )

    if workout is None:
        raise WorkoutSessionNotFoundError()

    return workout


async def get_active_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> WorkoutSession | None:
    return await workout_session_repository.get_active_workout_session(
        session,
        user_id=user_id,
    )


async def start_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    data: WorkoutSessionCreate,
) -> WorkoutSession:
    try:
        template = await _get_startable_template(
            session,
            user_id=user_id,
            template_id=data.template_id,
        )

        active_workout = await workout_session_repository.get_active_workout_session(
            session,
            user_id=user_id,
        )

        if active_workout is not None:
            raise ActiveWorkoutSessionExistsError()

        workout = await workout_session_repository.create_workout_session(
            session,
            user_id=user_id,
            template_id=template.id,
            name=template.name,
            exercises=_build_session_exercises(template),
        )

        saved_workout = await get_workout_session(
            session,
            user_id=user_id,
            session_id=workout.id,
        )

        await session.commit()

        return saved_workout
    except IntegrityError as error:
        await session.rollback()

        database_error = error.orig
        diagnostics = getattr(database_error, "diag", None)
        constraint_name = getattr(diagnostics, "constraint_name", None)
        sqlstate = getattr(database_error, "sqlstate", None)

        if sqlstate is None:
            database_error = database_error.__cause__
            constraint_name = getattr(database_error, "constraint_name", None)
            sqlstate = getattr(database_error, "sqlstate", None)

        if (
            sqlstate == "23505"
            and constraint_name == "uq_workout_sessions_user_in_progress"
        ):
            raise ActiveWorkoutSessionExistsError() from error

        raise
    except Exception:
        await session.rollback()
        raise


async def update_workout_session_set(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    set_id: UUID,
    data: WorkoutSessionSetUpdate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        workout_set = _find_session_set(
            workout,
            set_id=set_id,
        )

        _apply_set_update(workout_set, data)

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def update_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    data: WorkoutSessionUpdate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        workout.notes = data.notes

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def update_workout_session_exercise(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionExerciseUpdate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercise = next(
            (item for item in workout.exercises if item.id == exercise_id),
            None,
        )

        if exercise is None:
            raise WorkoutSessionExerciseNotFoundError()

        exercise.notes = data.notes

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def add_workout_session_exercise(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    data: WorkoutSessionExerciseCreate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercises = await exercise_repository.get_visible_exercises_by_ids(
            session,
            user_id=user_id,
            exercise_ids={data.exercise_id},
        )

        if not exercises:
            raise UnavailableExercisesError({data.exercise_id})

        exercise = exercises[0]

        next_position = (
            max(
                (item.position for item in workout.exercises),
                default=-1,
            )
            + 1
        )

        workout.exercises.append(
            WorkoutSessionExercise(
                exercise_id=exercise.id,
                position=next_position,
                exercise_snapshot={
                    "names": dict(exercise.names),
                    "muscle_groups": sorted(
                        group.code for group in exercise.muscle_groups
                    ),
                },
                notes=data.notes,
                sets=[
                    WorkoutSessionSet(
                        position=position,
                        set_type=set_data.set_type,
                        status="pending",
                    )
                    for position, set_data in enumerate(data.sets)
                ],
            )
        )

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def add_workout_session_set(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionSetCreate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercise = next(
            (item for item in workout.exercises if item.id == exercise_id),
            None,
        )

        if exercise is None:
            raise WorkoutSessionExerciseNotFoundError()

        next_position = (
            max(
                (item.position for item in exercise.sets),
                default=-1,
            )
            + 1
        )

        exercise.sets.append(
            WorkoutSessionSet(
                position=next_position,
                set_type=data.set_type,
                status="pending",
            )
        )

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def delete_workout_session_set(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    set_id: UUID,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        workout_set = _find_session_set(workout, set_id=set_id)

        exercise = next(
            item
            for item in workout.exercises
            if item.id == workout_set.session_exercise_id
        )

        if workout_set.status == "completed" or len(exercise.sets) <= 1:
            raise WorkoutSessionSetDeletionNotAllowedError()

        exercise.sets.remove(workout_set)

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def delete_workout_session_exercise(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    exercise_id: UUID,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercise = next(
            (item for item in workout.exercises if item.id == exercise_id),
            None,
        )

        if exercise is None:
            raise WorkoutSessionExerciseNotFoundError()

        if any(item.status == "completed" for item in exercise.sets):
            raise WorkoutSessionExerciseDeletionNotAllowedError()

        workout.exercises.remove(exercise)

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def replace_workout_session_exercise(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionExerciseCreate,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercise = next(
            (item for item in workout.exercises if item.id == exercise_id),
            None,
        )

        if exercise is None:
            raise WorkoutSessionExerciseNotFoundError()

        if any(item.status == "completed" for item in exercise.sets):
            raise WorkoutSessionExerciseReplacementNotAllowedError()

        available_exercises = await exercise_repository.get_visible_exercises_by_ids(
            session,
            user_id=user_id,
            exercise_ids={data.exercise_id},
        )

        if not available_exercises:
            raise UnavailableExercisesError({data.exercise_id})

        replacement = available_exercises[0]

        exercise.sets.clear()
        await session.flush()

        exercise.exercise_id = replacement.id
        exercise.exercise_snapshot = {
            "names": dict(replacement.names),
            "muscle_groups": sorted(group.code for group in replacement.muscle_groups),
        }
        exercise.notes = data.notes
        exercise.sets.extend(
            WorkoutSessionSet(
                position=position,
                set_type=set_data.set_type,
                status="pending",
            )
            for position, set_data in enumerate(data.sets)
        )

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def reorder_workout_session_exercises(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
    data: WorkoutSessionExercisesReorder,
) -> WorkoutSession:
    try:
        workout = await _get_active_session_for_update(
            session,
            user_id=user_id,
            session_id=session_id,
        )

        exercises_by_id = {exercise.id: exercise for exercise in workout.exercises}

        if len(data.exercise_ids) != len(exercises_by_id) or set(
            data.exercise_ids
        ) != set(exercises_by_id):
            raise InvalidWorkoutSessionExerciseOrderError()

        ordered_exercises = [
            exercises_by_id[exercise_id] for exercise_id in data.exercise_ids
        ]

        temporary_start = (
            max(
                (exercise.position for exercise in workout.exercises),
                default=-1,
            )
            + 1
        )

        for offset, exercise in enumerate(ordered_exercises):
            exercise.position = temporary_start + offset

        await session.flush()

        for position, exercise in enumerate(ordered_exercises):
            exercise.position = position

        await session.flush()

        workout.exercises.sort(key=lambda exercise: exercise.position)

        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def complete_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> WorkoutSession:
    try:
        workout = await workout_session_repository.get_workout_session_by_id(
            session,
            user_id=user_id,
            session_id=session_id,
            for_update=True,
        )

        if workout is None:
            raise WorkoutSessionNotFoundError()

        if workout.status == "completed":
            await session.commit()
            return workout

        if workout.status != "in_progress":
            raise WorkoutSessionCompletionNotAllowedError()

        sets = [
            workout_set
            for exercise in workout.exercises
            for workout_set in exercise.sets
        ]

        if not any(item.status == "completed" for item in sets):
            raise WorkoutSessionCompletionNotAllowedError()

        for workout_set in sets:
            if workout_set.status == "pending":
                workout_set.status = "skipped"

        workout.status = "completed"
        workout.completed_at = datetime.now(UTC)

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def cancel_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> WorkoutSession:
    try:
        workout = await workout_session_repository.get_workout_session_by_id(
            session,
            user_id=user_id,
            session_id=session_id,
            for_update=True,
        )

        if workout is None:
            raise WorkoutSessionNotFoundError()

        if workout.status == "cancelled":
            await session.commit()
            return workout

        if workout.status != "in_progress":
            raise WorkoutSessionCancellationNotAllowedError()

        workout.status = "cancelled"

        await session.flush()
        await session.commit()

        return workout
    except Exception:
        await session.rollback()
        raise


async def get_workout_session_history(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int,
    offset: int,
) -> WorkoutSessionHistoryRead:
    items, total = await workout_session_repository.get_workout_session_history(
        session,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return WorkoutSessionHistoryRead(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_workout_session_stats(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> WorkoutSessionStatsRead:
    (
        completed_count,
        average_duration,
    ) = await workout_session_repository.get_workout_session_stats(
        session,
        user_id=user_id,
    )

    return WorkoutSessionStatsRead(
        completed_sessions_count=completed_count,
        average_duration_seconds=average_duration,
    )

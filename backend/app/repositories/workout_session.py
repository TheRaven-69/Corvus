from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import WorkoutSession, WorkoutSessionExercise


async def get_workout_session_by_id(
    session: AsyncSession, *, session_id: UUID, user_id: UUID, for_update: bool = False
) -> WorkoutSession | None:
    statement = (
        select(WorkoutSession)
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == user_id,
        )
        .options(
            selectinload(WorkoutSession.exercises).selectinload(
                WorkoutSessionExercise.sets,
            ),
        )
        .execution_options(populate_existing=True)
    )

    if for_update:
        statement = statement.with_for_update()

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_active_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> WorkoutSession | None:
    statement = (
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == "in_progress",
        )
        .options(
            selectinload(WorkoutSession.exercises).selectinload(
                WorkoutSessionExercise.sets,
            ),
        )
        .execution_options(populate_existing=True)
    )
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def create_workout_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    template_id: UUID | None,
    name: str,
    exercises: list[WorkoutSessionExercise],
) -> WorkoutSession:
    workout = WorkoutSession(
        user_id=user_id,
        template_id=template_id,
        name=name,
        status="in_progress",
        exercises=exercises,
    )

    session.add(workout)
    await session.flush()

    return workout


async def get_workout_session_history(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[WorkoutSession], int]:
    filters = (
        WorkoutSession.user_id == user_id,
        WorkoutSession.status.in_(("completed", "cancelled")),
    )

    count_statement = select(func.count()).select_from(WorkoutSession).where(*filters)
    total = (await session.execute(count_statement)).scalar_one()

    statement = (
        select(WorkoutSession)
        .where(*filters)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(
                WorkoutSessionExercise.sets,
            ),
        )
        .order_by(
            WorkoutSession.started_at.desc(),
            WorkoutSession.id.desc(),
        )
        .limit(limit)
        .offset(offset)
        .execution_options(populate_existing=True)
    )

    result = await session.execute(statement)

    return list(result.scalars().all()), total


async def get_workout_session_stats(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> tuple[int, float | None]:
    duration_seconds = extract("epoch", WorkoutSession.completed_at) - extract(
        "epoch", WorkoutSession.started_at
    )

    statement = select(
        func.count(WorkoutSession.id),
        func.avg(duration_seconds),
    ).where(
        WorkoutSession.user_id == user_id,
        WorkoutSession.status == "completed",
    )

    result = await session.execute(statement)
    completed_count, average_duration = result.one()

    return (
        completed_count,
        float(average_duration) if average_duration is not None else None,
    )

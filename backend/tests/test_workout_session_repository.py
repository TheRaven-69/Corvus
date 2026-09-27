from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.repositories.workout_session import (
    create_workout_session,
    get_active_workout_session,
    get_workout_session_by_id,
)
from app.schemas.workout_session import WorkoutSessionRead
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.parametrize("commit", [False, True])
@pytest.mark.asyncio
async def test_create_session_persists_tree_only_when_caller_commits(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID], commit: bool
) -> None:
    _, _, owner_id = saved_workout
    exercises = [
        WorkoutSessionExercise(
            position=0,
            exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
            sets=[WorkoutSessionSet(position=0, set_type="working", planned_reps=8)],
        )
    ]
    workout = await create_workout_session(
        db_session,
        user_id=owner_id,
        template_id=None,
        name="New",
        exercises=exercises,
    )
    ids = (workout.id, workout.exercises[0].id, workout.exercises[0].sets[0].id)
    assert all(ids)
    assert workout.started_at is not None
    assert workout.status == "in_progress"
    assert workout.exercises[0].session_id == workout.id
    assert workout.exercises[0].sets[0].session_exercise_id == workout.exercises[0].id
    assert workout.exercises[0].sets[0].status == "pending"
    if commit:
        await db_session.commit()
    else:
        await db_session.rollback()
    db_session.expunge_all()
    for model, item_id in zip(
        [WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet], ids, strict=True
    ):
        assert (await db_session.get(model, item_id) is not None) == commit
    if commit:
        saved = await get_workout_session_by_id(
            db_session, session_id=ids[0], user_id=owner_id
        )
        assert saved is not None
        assert saved.name == "New"
        assert saved.exercises[0].sets[0].planned_reps == 8


@pytest.mark.asyncio
async def test_create_session_invalid_child_rolls_back_entire_tree(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID]
) -> None:
    _, _, owner_id = saved_workout
    models = [WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet]
    counts_before = [
        await db_session.scalar(select(func.count()).select_from(model))
        for model in models
    ]
    with pytest.raises(IntegrityError):
        await create_workout_session(
            db_session,
            user_id=owner_id,
            template_id=None,
            name="Invalid",
            exercises=[
                WorkoutSessionExercise(
                    position=0,
                    exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                    sets=[
                        WorkoutSessionSet(
                            position=0, set_type="working", planned_reps=0
                        )
                    ],
                )
            ],
        )
    await db_session.rollback()
    assert [
        await db_session.scalar(select(func.count()).select_from(model))
        for model in models
    ] == counts_before


@pytest.mark.asyncio
async def test_active_session_loads_owned_ordered_tree(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID]
) -> None:
    session_id, owner_id, other_id = saved_workout
    other_workout = WorkoutSession(user_id=other_id, name="Other user's workout")
    db_session.add(other_workout)
    await db_session.commit()
    other_session_id = other_workout.id
    db_session.expunge_all()

    workout = await get_active_workout_session(db_session, user_id=owner_id)
    other = await get_active_workout_session(db_session, user_id=other_id)
    assert workout is not None and workout.id == session_id
    assert other is not None and other.id == other_session_id
    db_session.expunge_all()
    result = WorkoutSessionRead.model_validate(workout)
    assert [item.position for item in result.exercises] == [0, 1]
    assert all(
        [item.position for item in exercise.sets] == [0, 1]
        for exercise in result.exercises
    )


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_active_session_excludes_closed_sessions(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID], status: str
) -> None:
    session_id, owner_id, _ = saved_workout
    workout = await db_session.get(WorkoutSession, session_id)
    assert workout is not None
    workout.status = status
    workout.started_at = datetime(2026, 9, 18, 10, tzinfo=UTC)
    workout.completed_at = (
        workout.started_at + timedelta(hours=1) if status == "completed" else None
    )
    await db_session.commit()
    assert await get_active_workout_session(db_session, user_id=owner_id) is None

    active = WorkoutSession(user_id=owner_id, name="New workout")
    db_session.add(active)
    await db_session.commit()
    result = await get_active_workout_session(db_session, user_id=owner_id)
    assert result is not None and result.id == active.id


@pytest.mark.asyncio
async def test_active_session_returns_none_when_user_has_no_sessions(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID]
) -> None:
    _, _, other_id = saved_workout
    assert await get_active_workout_session(db_session, user_id=other_id) is None


@pytest_asyncio.fixture
async def saved_workout(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="User",
            password_hash="not-a-real-hash",
        )
        for name in ["owner", "other"]
    ]
    db_session.add_all(users)
    await db_session.flush()
    workout = WorkoutSession(
        user_id=users[0].id,
        name="Strength",
        exercises=[
            WorkoutSessionExercise(
                position=position,
                exercise_snapshot={"names": {"en": name}, "muscle_groups": []},
                sets=[
                    WorkoutSessionSet(
                        position=index, set_type="working", planned_reps=reps
                    )
                    for index, reps in [(1, 8), (0, 10)]
                ],
            )
            for position, name in [(1, "Squat"), (0, "Bench press")]
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    result = (workout.id, users[0].id, users[1].id)
    db_session.expunge_all()
    return result


@pytest.mark.asyncio
async def test_get_session_loads_ordered_tree_without_lazy_queries(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID]
) -> None:
    session_id, owner_id, _ = saved_workout
    workout = await get_workout_session_by_id(
        db_session, session_id=session_id, user_id=owner_id
    )
    assert workout is not None
    db_session.expunge_all()
    result = WorkoutSessionRead.model_validate(workout)
    assert result.id == session_id
    assert [item.position for item in result.exercises] == [0, 1]
    assert [item.exercise_snapshot.names["en"] for item in result.exercises] == [
        "Bench press",
        "Squat",
    ]
    for item in result.exercises:
        assert [entry.position for entry in item.sets] == [0, 1]
        assert [entry.planned_reps for entry in item.sets] == [10, 8]


@pytest.mark.parametrize("case", ["other_owner", "missing"])
@pytest.mark.asyncio
async def test_get_session_hides_other_users_and_missing_resources(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID], case: str
) -> None:
    session_id, owner_id, other_id = saved_workout
    # An object already in the identity map must not bypass the ownership filter.
    assert (
        await get_workout_session_by_id(
            db_session, session_id=session_id, user_id=owner_id
        )
        is not None
    )
    result = await get_workout_session_by_id(
        db_session,
        session_id=session_id if case == "other_owner" else uuid4(),
        user_id=other_id if case == "other_owner" else owner_id,
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_session_refreshes_loaded_child_collections(
    db_session: AsyncSession, saved_workout: tuple[UUID, UUID, UUID]
) -> None:
    session_id, owner_id, _ = saved_workout
    workout = await get_workout_session_by_id(
        db_session, session_id=session_id, user_id=owner_id
    )
    assert workout is not None
    removed_exercise_id = workout.exercises[1].id
    removed_set_id = workout.exercises[0].sets[1].id
    await db_session.execute(
        delete(WorkoutSessionExercise)
        .where(WorkoutSessionExercise.id == removed_exercise_id)
        .execution_options(synchronize_session=False)
    )
    await db_session.execute(
        delete(WorkoutSessionSet)
        .where(WorkoutSessionSet.id == removed_set_id)
        .execution_options(synchronize_session=False)
    )
    await db_session.commit()
    refreshed = await get_workout_session_by_id(
        db_session, session_id=session_id, user_id=owner_id
    )
    assert refreshed is workout
    assert len(refreshed.exercises) == 1
    assert len(refreshed.exercises[0].sets) == 1
    assert refreshed.exercises[0].sets[0].position == 0

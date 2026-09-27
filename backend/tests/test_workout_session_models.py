from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutTemplate,
)
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

START = datetime(2026, 9, 16, 10, tzinfo=UTC)
END = START + timedelta(hours=1)


@pytest.mark.asyncio
async def test_session_exercises_persist_and_load_in_position_order(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    workout = WorkoutSession(
        user_id=owner_id,
        name="Ordered workout",
        exercises=[
            WorkoutSessionExercise(
                position=position,
                exercise_snapshot={"names": {"en": name}, "muscle_groups": []},
            )
            for position, name in [(1, "Squat"), (0, "Bench press")]
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    workout_id = workout.id
    db_session.expunge_all()

    saved = await db_session.scalar(
        select(WorkoutSession)
        .where(WorkoutSession.id == workout_id)
        .options(selectinload(WorkoutSession.exercises))
    )
    assert saved is not None
    assert [item.position for item in saved.exercises] == [0, 1]
    assert [item.exercise_snapshot["names"] for item in saved.exercises] == [
        {"en": "Bench press"},
        {"en": "Squat"},
    ]
    assert all(item.session_id == workout_id for item in saved.exercises)
    assert all(item.session is saved for item in saved.exercises)


@pytest.mark.parametrize("load_exercises", [False, True])
@pytest.mark.asyncio
async def test_deleting_session_removes_its_exercises_but_preserves_catalog(
    db_session: AsyncSession, owner_id: UUID, load_exercises: bool
) -> None:
    exercise = Exercise(code="shared_squat", names={"en": "Squat"})
    db_session.add(exercise)
    await db_session.flush()
    workouts = [
        WorkoutSession(
            user_id=owner_id,
            name=name,
            status="cancelled",
            exercises=[
                WorkoutSessionExercise(
                    position=0,
                    exercise_id=exercise.id,
                    exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                )
            ],
        )
        for name in ["Delete", "Keep"]
    ]
    db_session.add_all(workouts)
    await db_session.commit()
    deleted_id, kept_id = [workout.id for workout in workouts]
    exercise_id = exercise.id
    db_session.expunge_all()

    query = select(WorkoutSession).where(WorkoutSession.id == deleted_id)
    if load_exercises:
        query = query.options(selectinload(WorkoutSession.exercises))
    saved = await db_session.scalar(query)
    assert saved is not None
    await db_session.delete(saved)
    await db_session.commit()
    db_session.expunge_all()

    remaining = (await db_session.scalars(select(WorkoutSessionExercise))).all()
    assert [item.session_id for item in remaining] == [kept_id]
    assert await db_session.get(WorkoutSession, deleted_id) is None
    assert await db_session.get(Exercise, exercise_id) is not None


@pytest.mark.asyncio
async def test_removing_exercise_from_session_deletes_only_that_child(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    workout = WorkoutSession(
        user_id=owner_id,
        name="Keep session",
        exercises=[
            WorkoutSessionExercise(
                position=position,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
            )
            for position in [0, 1]
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    workout_id = workout.id
    removed_id = workout.exercises[1].id
    kept_id = workout.exercises[0].id
    workout.exercises.pop()
    await db_session.commit()
    db_session.expunge_all()

    assert await db_session.get(WorkoutSessionExercise, removed_id) is None
    assert await db_session.get(WorkoutSessionExercise, kept_id) is not None
    assert await db_session.get(WorkoutSession, workout_id) is not None


@pytest.mark.parametrize("catalog_action", ["rename", "delete"])
@pytest.mark.asyncio
async def test_catalog_changes_preserve_session_exercise_snapshot(
    db_session: AsyncSession, owner_id: UUID, catalog_action: str
) -> None:
    exercise = Exercise(code="squat", names={"en": "Squat"})
    workout = WorkoutSession(
        user_id=owner_id,
        name="History",
        status="completed",
        started_at=START,
        completed_at=END,
    )
    db_session.add_all([exercise, workout])
    await db_session.flush()
    snapshot = {"names": {"en": "Squat"}, "muscle_groups": ["quadriceps"]}
    item = WorkoutSessionExercise(
        session_id=workout.id,
        exercise_id=exercise.id,
        position=0,
        exercise_snapshot=snapshot,
        notes="Keep this note",
    )
    db_session.add(item)
    await db_session.commit()
    item_id, exercise_id = item.id, exercise.id
    if catalog_action == "delete":
        await db_session.execute(delete(Exercise).where(Exercise.id == exercise_id))
    else:
        exercise.names = {"en": "Renamed squat"}
    await db_session.commit()
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionExercise, item_id)
    assert saved is not None, "Catalog deletion must not erase workout history"
    assert saved.exercise_snapshot == snapshot
    assert saved.notes == "Keep this note"
    assert saved.position == 0
    assert saved.exercise_id == (None if catalog_action == "delete" else exercise_id)


@pytest.mark.parametrize("positions", [[-1], [0, 0]])
@pytest.mark.asyncio
async def test_session_exercise_rejects_invalid_positions(
    db_session: AsyncSession, owner_id: UUID, positions: list[int]
) -> None:
    workout = WorkoutSession(user_id=owner_id, name="Positions")
    db_session.add(workout)
    await db_session.commit()
    db_session.add_all(
        [
            WorkoutSessionExercise(
                session_id=workout.id,
                position=position,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
            )
            for position in positions
        ]
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_session_saved_through_user_relationship(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="relationship@example.com",
        username="relationship_owner",
        first_name="Session",
        last_name="Owner",
        password_hash="not-a-real-hash",
        workout_sessions=[WorkoutSession(name="Strength")],
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    workout_id = user.workout_sessions[0].id
    db_session.expunge_all()

    saved = await db_session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.workout_sessions))
    )
    assert saved is not None
    assert [workout.id for workout in saved.workout_sessions] == [workout_id]
    assert saved.workout_sessions[0].user_id == user_id
    assert saved.workout_sessions[0].user is saved


@pytest.mark.parametrize("load_sessions", [False, True])
@pytest.mark.asyncio
async def test_orm_user_deletion_removes_loaded_or_unloaded_sessions(
    db_session: AsyncSession, owner_id: UUID, load_sessions: bool
) -> None:
    db_session.add(WorkoutSession(user_id=owner_id, name="Private"))
    await db_session.commit()
    db_session.expunge_all()
    query = select(User).where(User.id == owner_id)
    if load_sessions:
        query = query.options(selectinload(User.workout_sessions))
    user = await db_session.scalar(query)
    assert user is not None
    await db_session.delete(user)
    await db_session.commit()
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 0
    )


@pytest.mark.asyncio
async def test_removing_session_from_user_collection_deletes_only_that_session(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    db_session.add_all(
        [
            WorkoutSession(user_id=owner_id, name="Active"),
            WorkoutSession(user_id=owner_id, name="Cancelled", status="cancelled"),
        ]
    )
    await db_session.commit()
    db_session.expunge_all()
    user = await db_session.scalar(
        select(User)
        .where(User.id == owner_id)
        .options(selectinload(User.workout_sessions))
    )
    assert user is not None
    removed = next(
        item for item in user.workout_sessions if item.status == "in_progress"
    )
    user.workout_sessions.remove(removed)
    await db_session.commit()
    db_session.expunge_all()

    assert await db_session.get(WorkoutSession, removed.id) is None
    assert await db_session.get(User, owner_id) is not None
    remaining = (await db_session.scalars(select(WorkoutSession))).all()
    assert [item.name for item in remaining] == ["Cancelled"]


@pytest_asyncio.fixture
async def owner_id(db_session: AsyncSession) -> UUID:
    user = User(
        email="session-owner@example.com",
        username="session_owner",
        first_name="Session",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )
    db_session.add(user)
    await db_session.commit()
    return user.id


@pytest.mark.asyncio
async def test_session_defaults_and_nullable_fields(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    workout = WorkoutSession(user_id=owner_id, name="Strength")
    db_session.add(workout)
    await db_session.commit()
    await db_session.refresh(workout)

    assert workout.id is not None
    assert workout.status == "in_progress"
    assert workout.started_at is not None
    assert workout.completed_at is None
    assert workout.template_id is None
    assert workout.notes is None


@pytest.mark.parametrize(
    ("status", "completed_at"),
    [
        ("unknown", None),
        ("completed", None),
        ("in_progress", END),
        ("cancelled", END),
        ("completed", START - timedelta(seconds=1)),
    ],
)
@pytest.mark.asyncio
async def test_session_rejects_invalid_status_or_time(
    db_session: AsyncSession,
    owner_id: UUID,
    status: str,
    completed_at: datetime | None,
) -> None:
    db_session.add(
        WorkoutSession(
            user_id=owner_id,
            name="Invalid",
            status=status,
            started_at=START,
            completed_at=completed_at,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_second_active_session_is_rejected(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    first = WorkoutSession(user_id=owner_id, name="First")
    db_session.add(first)
    await db_session.commit()
    first_id = first.id
    db_session.add(WorkoutSession(user_id=owner_id, name="Second"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    saved = (await db_session.scalars(select(WorkoutSession))).all()
    assert [item.id for item in saved] == [first_id]


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_closed_sessions_allow_another_active_session(
    db_session: AsyncSession, owner_id: UUID, status: str
) -> None:
    workout = WorkoutSession(user_id=owner_id, name="First", started_at=START)
    db_session.add(workout)
    await db_session.commit()
    workout.status = status
    workout.completed_at = END if status == "completed" else None
    await db_session.commit()

    db_session.add_all(
        [
            WorkoutSession(
                user_id=owner_id,
                name="Another closed session",
                status=status,
                started_at=START,
                completed_at=END if status == "completed" else None,
            ),
            WorkoutSession(user_id=owner_id, name="New active session"),
        ]
    )
    await db_session.commit()
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 3
    )


@pytest.mark.asyncio
async def test_different_users_can_have_active_sessions(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    other = User(
        email="other@example.com",
        username="other",
        first_name="Other",
        last_name="User",
        password_hash="not-a-real-hash",
    )
    db_session.add(other)
    await db_session.flush()
    db_session.add_all(
        [
            WorkoutSession(user_id=user_id, name="Active")
            for user_id in (owner_id, other.id)
        ]
    )
    await db_session.commit()
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 2
    )


@pytest.mark.asyncio
async def test_template_deletion_preserves_completed_session(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    template = WorkoutTemplate(user_id=owner_id, name="Original")
    db_session.add(template)
    await db_session.flush()
    workout = WorkoutSession(
        user_id=owner_id,
        template_id=template.id,
        name="Original",
        status="completed",
        started_at=START,
        completed_at=END,
        notes="Keep this record",
    )
    db_session.add(workout)
    await db_session.commit()
    await db_session.execute(
        delete(WorkoutTemplate).where(WorkoutTemplate.id == template.id)
    )
    await db_session.commit()
    await db_session.refresh(workout)

    assert workout.template_id is None
    assert workout.name == "Original"
    assert workout.status == "completed"
    assert workout.completed_at - workout.started_at == timedelta(hours=1)
    assert workout.notes == "Keep this record"


@pytest.mark.asyncio
async def test_user_deletion_removes_sessions(
    db_session: AsyncSession, owner_id: UUID
) -> None:
    db_session.add(WorkoutSession(user_id=owner_id, name="Private"))
    await db_session.commit()
    await db_session.execute(delete(User).where(User.id == owner_id))
    await db_session.commit()
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 0
    )


@pytest.mark.parametrize("missing_parent", ["user", "template"])
@pytest.mark.asyncio
async def test_session_rejects_missing_parent(
    db_session: AsyncSession, owner_id: UUID, missing_parent: str
) -> None:
    db_session.add(
        WorkoutSession(
            user_id=uuid4() if missing_parent == "user" else owner_id,
            template_id=uuid4() if missing_parent == "template" else None,
            name="Invalid reference",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

COMPLETED_AT = datetime(2026, 9, 16, 11, tzinfo=UTC)


@pytest.mark.asyncio
async def test_sets_save_through_relationship_and_load_in_order(
    db_session: AsyncSession, exercise_ids: list[UUID]
) -> None:
    exercise = await db_session.scalar(
        select(WorkoutSessionExercise)
        .where(WorkoutSessionExercise.id == exercise_ids[0])
        .options(selectinload(WorkoutSessionExercise.sets))
    )
    assert exercise is not None
    exercise.sets = [
        WorkoutSessionSet(position=1, set_type="working", actual_reps=8),
        WorkoutSessionSet(position=0, set_type="warmup", actual_reps=12),
    ]
    await db_session.commit()
    db_session.expunge_all()
    saved = await db_session.scalar(
        select(WorkoutSessionExercise)
        .where(WorkoutSessionExercise.id == exercise_ids[0])
        .options(selectinload(WorkoutSessionExercise.sets))
    )
    assert saved is not None
    assert [item.position for item in saved.sets] == [0, 1]
    assert [item.actual_reps for item in saved.sets] == [12, 8]
    assert all(item.session_exercise_id == saved.id for item in saved.sets)
    assert all(item.session_exercise is saved for item in saved.sets)
    removed_id = saved.sets[1].id
    saved.sets.pop()
    await db_session.commit()
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionSet, removed_id) is None
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 1
    )
    assert await db_session.get(WorkoutSessionExercise, exercise_ids[0]) is not None


@pytest.mark.parametrize("level", ["user", "session", "exercise"])
@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.asyncio
async def test_deletion_cascades_through_session_tree(
    db_session: AsyncSession, exercise_ids: list[UUID], level: str, loaded: bool
) -> None:
    db_session.add_all(
        [
            WorkoutSessionSet(
                session_exercise_id=exercise_id, position=0, set_type="working"
            )
            for exercise_id in exercise_ids
        ]
    )
    await db_session.commit()
    db_session.expunge_all()
    model = {
        "user": User,
        "session": WorkoutSession,
        "exercise": WorkoutSessionExercise,
    }[level]
    query = select(model)
    if level == "exercise":
        query = query.where(WorkoutSessionExercise.id == exercise_ids[0])
    if loaded:
        option = {
            "user": selectinload(User.workout_sessions)
            .selectinload(WorkoutSession.exercises)
            .selectinload(WorkoutSessionExercise.sets),
            "session": selectinload(WorkoutSession.exercises).selectinload(
                WorkoutSessionExercise.sets
            ),
            "exercise": selectinload(WorkoutSessionExercise.sets),
        }[level]
        query = query.options(option)
    target = await db_session.scalar(query)
    assert target is not None
    await db_session.delete(target)
    await db_session.commit()
    db_session.expunge_all()
    expected_counts = {
        "user": (0, 0, 0, 0),
        "session": (1, 0, 0, 0),
        "exercise": (1, 1, 1, 1),
    }[level]
    for entity, expected in zip(
        [User, WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet],
        expected_counts,
        strict=True,
    ):
        assert (
            await db_session.scalar(select(func.count()).select_from(entity))
            == expected
        )


@pytest_asyncio.fixture
async def exercise_ids(db_session: AsyncSession) -> list[UUID]:
    workout = WorkoutSession(
        name="Strength",
        user=User(
            email="sets@example.com",
            username="sets_owner",
            first_name="Set",
            last_name="Owner",
            password_hash="not-a-real-hash",
        ),
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
    return [exercise.id for exercise in workout.exercises]


@pytest.mark.parametrize(
    "values",
    [
        {"position": -1},
        {"set_type": "invalid"},
        {"status": "invalid"},
        {"planned_reps": 0},
        {"planned_reps": -1},
        {"actual_reps": 0},
        {"actual_reps": -1},
        {"planned_weight_kg": Decimal("-0.01")},
        {"actual_weight_kg": Decimal("-0.01")},
        {"status": "completed"},
        {"status": "completed", "actual_reps": 5},
        {"status": "completed", "completed_at": COMPLETED_AT},
        {"status": "pending", "actual_reps": 5, "completed_at": COMPLETED_AT},
        {"status": "skipped", "actual_reps": 5, "completed_at": COMPLETED_AT},
        {"session_exercise_id": uuid4()},
    ],
)
@pytest.mark.asyncio
async def test_set_rejects_invalid_values(
    db_session: AsyncSession, exercise_ids: list[UUID], values: dict[str, object]
) -> None:
    fields = {
        "session_exercise_id": exercise_ids[0],
        "position": 0,
        "set_type": "working",
    }
    fields.update(values)
    db_session.add(WorkoutSessionSet(**fields))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.parametrize("status", ["pending", "skipped", "completed"])
@pytest.mark.parametrize("weight", [None, Decimal("0.00"), Decimal("62.25")])
@pytest.mark.asyncio
async def test_set_preserves_plan_and_actual_values(
    db_session: AsyncSession,
    exercise_ids: list[UUID],
    status: str,
    weight: Decimal | None,
) -> None:
    item = WorkoutSessionSet(
        session_exercise_id=exercise_ids[0],
        position=0,
        set_type="working",
        planned_reps=10,
        planned_weight_kg=Decimal("60.50"),
        actual_reps=8,
        actual_weight_kg=weight,
        status=status,
        completed_at=COMPLETED_AT if status == "completed" else None,
    )
    db_session.add(item)
    await db_session.commit()
    item_id = item.id
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionSet, item_id)
    assert saved is not None
    assert saved.planned_reps == 10
    assert saved.planned_weight_kg == Decimal("60.50")
    assert saved.actual_reps == 8
    assert saved.actual_weight_kg == weight
    assert saved.status == status
    assert (saved.completed_at is not None) == (status == "completed")


@pytest.mark.asyncio
async def test_added_set_allows_empty_plan_and_results(
    db_session: AsyncSession, exercise_ids: list[UUID]
) -> None:
    item = WorkoutSessionSet(
        session_exercise_id=exercise_ids[0], position=0, set_type="warmup"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.status == "pending"
    assert item.planned_reps is None
    assert item.planned_weight_kg is None
    assert item.actual_reps is None
    assert item.actual_weight_kg is None
    assert item.completed_at is None


@pytest.mark.parametrize("same_exercise", [True, False])
@pytest.mark.asyncio
async def test_set_position_is_unique_within_its_exercise(
    db_session: AsyncSession, exercise_ids: list[UUID], same_exercise: bool
) -> None:
    db_session.add(
        WorkoutSessionSet(
            session_exercise_id=exercise_ids[0], position=0, set_type="working"
        )
    )
    await db_session.commit()
    db_session.add(
        WorkoutSessionSet(
            session_exercise_id=exercise_ids[0 if same_exercise else 1],
            position=0,
            set_type="warmup",
        )
    )
    if same_exercise:
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
    else:
        await db_session.commit()

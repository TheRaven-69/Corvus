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
from app.schemas.workout_session import WorkoutSessionSetUpdate
from app.services import workout_session as service
from app.services.exceptions import (
    InvalidWorkoutSessionSetError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
    WorkoutSessionSetNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession

NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


@pytest_asyncio.fixture
async def recording(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    user = User(
        email="record@example.com",
        username="record",
        first_name="Record",
        last_name="Owner",
        password_hash="test",
    )
    item = WorkoutSessionSet(
        position=0,
        set_type="working",
        planned_reps=10,
        planned_weight_kg=Decimal("60.00"),
    )
    workout = WorkoutSession(
        user=user,
        name="Record",
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                sets=[item],
            )
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    return user.id, workout.id, item.id


async def update(
    session: AsyncSession, ids: tuple[UUID, UUID, UUID], payload: dict[str, object]
) -> WorkoutSessionSet:
    workout = await service.update_workout_session_set(
        session,
        user_id=ids[0],
        session_id=ids[1],
        set_id=ids[2],
        data=WorkoutSessionSetUpdate.model_validate(payload),
    )
    return workout.exercises[0].sets[0]


@pytest.mark.asyncio
async def test_record_complete_correct_and_reopen_preserves_plan(
    db_session: AsyncSession,
    recording: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Clock:
        @staticmethod
        def now(tz) -> datetime:
            assert tz is UTC
            return NOW

    monkeypatch.setattr(service, "datetime", Clock)
    item = await update(
        db_session, recording, {"actual_reps": 8, "actual_weight_kg": "62.25"}
    )
    assert item.status == "pending" and item.completed_at is None
    item = await update(db_session, recording, {"status": "completed"})
    assert item.completed_at == NOW
    item = await update(db_session, recording, {"actual_reps": 9})
    assert item.completed_at.replace(tzinfo=UTC) == NOW
    assert item.actual_weight_kg == Decimal("62.25")
    item = await update(db_session, recording, {"status": "pending"})
    assert item.completed_at is None and item.actual_reps == 9
    item = await update(
        db_session, recording, {"actual_weight_kg": None, "status": "skipped"}
    )
    assert item.actual_weight_kg is None and item.actual_reps == 9
    assert item.planned_reps == 10 and item.planned_weight_kg == Decimal("60.00")
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionSet, recording[2])
    assert saved is not None and saved.status == "skipped"


@pytest.mark.parametrize("already_completed", [False, True])
@pytest.mark.asyncio
async def test_completed_set_requires_reps_and_rejection_preserves_data(
    db_session: AsyncSession,
    recording: tuple[UUID, UUID, UUID],
    already_completed: bool,
) -> None:
    if already_completed:
        await update(db_session, recording, {"actual_reps": 8, "status": "completed"})
    with pytest.raises(InvalidWorkoutSessionSetError):
        await update(
            db_session,
            recording,
            {"actual_reps": None, "status": "completed", "actual_weight_kg": "99"},
        )
    saved = await db_session.get(WorkoutSessionSet, recording[2])
    assert saved is not None
    assert saved.actual_weight_kg is None
    assert saved.actual_reps == (8 if already_completed else None)


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_closed_session_cannot_be_edited(
    db_session: AsyncSession, recording: tuple[UUID, UUID, UUID], status: str
) -> None:
    workout = await db_session.get(WorkoutSession, recording[1])
    assert workout is not None
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await update(db_session, recording, {"actual_reps": 8})


@pytest.mark.parametrize("field", [0, 1, 2])
@pytest.mark.asyncio
async def test_update_rejects_wrong_owner_session_or_set(
    db_session: AsyncSession, recording: tuple[UUID, UUID, UUID], field: int
) -> None:
    ids = list(recording)
    ids[field] = uuid4()
    error = (
        WorkoutSessionSetNotFoundError if field == 2 else WorkoutSessionNotFoundError
    )
    with pytest.raises(error):
        await update(db_session, tuple(ids), {"actual_reps": 8})
    item = await db_session.get(WorkoutSessionSet, recording[2])
    assert item is not None and item.actual_reps is None


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_set_changes(
    db_session: AsyncSession,
    recording: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError, match="Commit failed"):
        await update(db_session, recording, {"actual_reps": 8, "status": "completed"})
    item = await db_session.get(WorkoutSessionSet, recording[2])
    assert item is not None and item.status == "pending"
    assert item.actual_reps is None and item.completed_at is None

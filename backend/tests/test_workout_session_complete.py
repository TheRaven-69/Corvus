from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.schemas.workout_session import WorkoutSessionRead
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionCompletionNotAllowedError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    user = User(
        email="complete@example.com",
        username="complete",
        first_name="Test",
        last_name="Owner",
        password_hash="test",
    )
    start = datetime.now(UTC) - timedelta(hours=1)
    workout = WorkoutSession(
        user=user,
        name="Finish",
        started_at=start,
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                sets=[
                    WorkoutSessionSet(
                        position=0,
                        set_type="working",
                        status="completed",
                        actual_reps=8,
                        actual_weight_kg=25,
                        completed_at=start + timedelta(minutes=10),
                    ),
                    WorkoutSessionSet(position=1, set_type="working", status="pending"),
                    WorkoutSessionSet(position=2, set_type="working", status="skipped"),
                ],
            )
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    return user.id, workout.id


@pytest.mark.asyncio
async def test_complete_persists_duration_and_preserves_results(
    db_session: AsyncSession, context
) -> None:
    owner, workout_id = context
    before = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    completed = before.exercises[0].sets[0]
    completed_id, completed_at = completed.id, completed.completed_at
    start = before.started_at.replace(tzinfo=UTC)
    lower = datetime.now(UTC)
    result = await service.complete_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    assert result.status == "completed"
    assert lower <= result.completed_at <= datetime.now(UTC)
    assert [s.status for s in result.exercises[0].sets] == [
        "completed",
        "skipped",
        "skipped",
    ]
    item = result.exercises[0].sets[0]
    assert (
        item.id == completed_id
        and item.actual_reps == 8
        and item.actual_weight_kg == 25
    )
    assert item.completed_at == completed_at
    assert all(s.completed_at is None for s in result.exercises[0].sets[1:])
    end = result.completed_at
    db_session.expunge_all()
    saved = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    # SQLite reloads timestamps without timezone information.
    assert saved.completed_at.replace(tzinfo=UTC) == end
    assert WorkoutSessionRead.model_validate(saved).duration_seconds == int(
        (end - start).total_seconds()
    )
    assert await service.get_active_workout_session(db_session, user_id=owner) is None
    db_session.add(WorkoutSession(user_id=owner, name="Next"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_complete_repeated_request_keeps_original_timestamp(
    db_session: AsyncSession, context
) -> None:
    owner, workout_id = context
    await service.complete_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    db_session.expunge_all()
    first = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    expected = WorkoutSessionRead.model_validate(first).model_dump()
    result = await service.complete_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    assert WorkoutSessionRead.model_validate(result).model_dump() == expected
    assert not db_session.in_transaction()


@pytest.mark.parametrize(
    "case", ["empty", "pending", "skipped", "cancelled", "other_user", "missing"]
)
@pytest.mark.asyncio
async def test_complete_rejects_invalid_workout(
    db_session: AsyncSession, context, case: str
) -> None:
    owner, workout_id = context
    workout = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    if case == "empty":
        workout.exercises.clear()
    elif case in {"pending", "skipped"}:
        for item in workout.exercises[0].sets:
            item.status = case
            item.completed_at = None
    elif case == "cancelled":
        workout.status = "cancelled"
    await db_session.commit()
    original_status = workout.status
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing"}
        else WorkoutSessionCompletionNotAllowedError
    )
    with pytest.raises(error):
        await service.complete_workout_session(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing" else workout_id,
        )
    saved = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    assert saved.status == original_status and saved.completed_at is None


@pytest.mark.asyncio
async def test_complete_rolls_back_statuses_and_timestamp(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    owner, workout_id = context
    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.complete_workout_session(
            db_session, user_id=owner, session_id=workout_id
        )
    db_session.expunge_all()
    saved = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    assert saved.status == "in_progress" and saved.completed_at is None
    assert [s.status for s in saved.exercises[0].sets] == [
        "completed",
        "pending",
        "skipped",
    ]

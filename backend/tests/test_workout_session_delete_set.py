from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.schemas.workout_session import WorkoutSessionSetCreate
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
    WorkoutSessionSetDeletionNotAllowedError,
    WorkoutSessionSetNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    user = User(
        email="delete@example.com",
        username="delete",
        first_name="Test",
        last_name="Owner",
        password_hash="test",
    )
    workouts = [
        WorkoutSession(
            user=user,
            name=status,
            status=status,
            exercises=[
                WorkoutSessionExercise(
                    position=0,
                    exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                    sets=[
                        WorkoutSessionSet(
                            position=i, set_type="working", planned_reps=8
                        )
                        for i in range(3)
                    ],
                )
            ],
        )
        for status in ["in_progress", "cancelled"]
    ]
    db_session.add_all(workouts)
    await db_session.commit()
    return (
        user.id,
        workouts[0].id,
        workouts[0].exercises[0].id,
        [s.id for s in workouts[0].exercises[0].sets],
        workouts[1].exercises[0].sets[0].id,
    )


@pytest.mark.parametrize("status", ["pending", "skipped"])
@pytest.mark.asyncio
async def test_delete_set_persists_and_preserves_order(
    db_session: AsyncSession, context, status: str
) -> None:
    owner, workout_id, exercise_id, ids, _ = context
    item = await db_session.get(WorkoutSessionSet, ids[1])
    item.status = status
    await db_session.commit()
    result = await service.delete_workout_session_set(
        db_session, user_id=owner, session_id=workout_id, set_id=ids[1]
    )
    assert [s.id for s in result.exercises[0].sets] == [ids[0], ids[2]]
    assert [s.position for s in result.exercises[0].sets] == [0, 2]
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionSet, ids[1]) is None
    result = await service.add_workout_session_set(
        db_session,
        user_id=owner,
        session_id=workout_id,
        exercise_id=exercise_id,
        data=WorkoutSessionSetCreate(),
    )
    assert [s.position for s in result.exercises[0].sets] == [0, 2, 3]
    assert result.exercises[0].sets[0].planned_reps == 8


@pytest.mark.asyncio
async def test_delete_completed_set_rejected(db_session: AsyncSession, context) -> None:
    owner, workout_id, _, ids, _ = context
    item = await db_session.get(WorkoutSessionSet, ids[1])
    item.status = "completed"
    item.actual_reps = 10
    item.completed_at = datetime.now(UTC)
    await db_session.commit()
    with pytest.raises(WorkoutSessionSetDeletionNotAllowedError):
        await service.delete_workout_session_set(
            db_session, user_id=owner, session_id=workout_id, set_id=ids[1]
        )
    saved = await db_session.get(WorkoutSessionSet, ids[1])
    assert saved.actual_reps == 10 and saved.status == "completed"


@pytest.mark.asyncio
async def test_delete_last_set_rejected(db_session: AsyncSession, context) -> None:
    owner, workout_id, _, ids, _ = context
    for set_id in ids[:2]:
        await service.delete_workout_session_set(
            db_session, user_id=owner, session_id=workout_id, set_id=set_id
        )
    with pytest.raises(WorkoutSessionSetDeletionNotAllowedError):
        await service.delete_workout_session_set(
            db_session, user_id=owner, session_id=workout_id, set_id=ids[2]
        )
    assert await db_session.get(WorkoutSessionSet, ids[2]) is not None


@pytest.mark.parametrize(
    "case", ["other_user", "missing_session", "other_set", "missing_set"]
)
@pytest.mark.asyncio
async def test_delete_set_rejects_wrong_resource(
    db_session: AsyncSession, context, case: str
) -> None:
    owner, workout_id, _, ids, foreign_id = context
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing_session"}
        else WorkoutSessionSetNotFoundError
    )
    with pytest.raises(error):
        await service.delete_workout_session_set(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing_session" else workout_id,
            set_id=foreign_id
            if case == "other_set"
            else uuid4()
            if case == "missing_set"
            else ids[1],
        )
    assert await db_session.get(WorkoutSessionSet, ids[1]) is not None
    assert await db_session.get(WorkoutSessionSet, foreign_id) is not None


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_delete_set_rejects_closed_session(
    db_session: AsyncSession, context, status: str
) -> None:
    owner, workout_id, _, ids, _ = context
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.delete_workout_session_set(
            db_session, user_id=owner, session_id=workout_id, set_id=ids[1]
        )
    assert await db_session.get(WorkoutSessionSet, ids[1]) is not None


@pytest.mark.asyncio
async def test_delete_set_rolls_back_failed_commit(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    owner, workout_id, _, ids, _ = context
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.delete_workout_session_set(
            db_session, user_id=owner, session_id=workout_id, set_id=ids[1]
        )
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionSet, ids[1])
    assert saved is not None and saved.position == 1

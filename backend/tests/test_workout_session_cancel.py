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
from app.schemas.workout_session import WorkoutSessionRead
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionCancellationNotAllowedError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    user = User(
        email="cancel@example.com",
        username="cancel",
        first_name="Test",
        last_name="Owner",
        password_hash="test",
    )
    workout = WorkoutSession(
        user=user,
        name="Cancel",
        notes="Keep",
        exercises=[
            WorkoutSessionExercise(
                position=0,
                notes="Keep exercise",
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                sets=[
                    WorkoutSessionSet(
                        position=0,
                        set_type="working",
                        status="completed",
                        actual_reps=8,
                        actual_weight_kg=25,
                        completed_at=datetime.now(UTC),
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


async def read(db_session: AsyncSession, owner, workout_id):
    workout = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    return WorkoutSessionRead.model_validate(workout).model_dump()


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.asyncio
async def test_cancel_preserves_data_and_allows_new_session(
    db_session: AsyncSession, context, empty: bool
) -> None:
    owner, workout_id = context
    if empty:
        workout = await service.get_workout_session(
            db_session, user_id=owner, session_id=workout_id
        )
        workout.exercises.clear()
        await db_session.commit()
    before = await read(db_session, owner, workout_id)
    result = await service.cancel_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    expected = {**before, "status": "cancelled"}
    assert WorkoutSessionRead.model_validate(result).model_dump() == expected
    db_session.expunge_all()
    assert await read(db_session, owner, workout_id) == expected
    assert await service.get_active_workout_session(db_session, user_id=owner) is None
    db_session.add(WorkoutSession(user_id=owner, name="Next"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_cancel_repeated_request_is_unchanged(
    db_session: AsyncSession, context
) -> None:
    owner, workout_id = context
    await service.cancel_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    before = await read(db_session, owner, workout_id)
    result = await service.cancel_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    assert WorkoutSessionRead.model_validate(result).model_dump() == before
    assert not db_session.in_transaction()


@pytest.mark.asyncio
async def test_cancel_rejects_completed_session(
    db_session: AsyncSession, context
) -> None:
    owner, workout_id = context
    await service.complete_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    db_session.expunge_all()
    before = await read(db_session, owner, workout_id)
    with pytest.raises(WorkoutSessionCancellationNotAllowedError):
        await service.cancel_workout_session(
            db_session, user_id=owner, session_id=workout_id
        )
    assert await read(db_session, owner, workout_id) == before


@pytest.mark.parametrize("case", ["other_user", "missing"])
@pytest.mark.asyncio
async def test_cancel_enforces_ownership(
    db_session: AsyncSession, context, case: str
) -> None:
    owner, workout_id = context
    before = await read(db_session, owner, workout_id)
    with pytest.raises(WorkoutSessionNotFoundError):
        await service.cancel_workout_session(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing" else workout_id,
        )
    assert await read(db_session, owner, workout_id) == before


@pytest.mark.asyncio
async def test_cancel_rolls_back_failed_commit(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    owner, workout_id = context
    before = await read(db_session, owner, workout_id)
    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.cancel_workout_session(
            db_session, user_id=owner, session_id=workout_id
        )
    db_session.expunge_all()
    assert await read(db_session, owner, workout_id) == before

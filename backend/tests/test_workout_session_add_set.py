from uuid import UUID, uuid4

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
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession) -> tuple[UUID, UUID, UUID, UUID]:
    user = User(
        email="sets@example.com",
        username="sets",
        first_name="Set",
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
                            position=3, set_type="working", planned_reps=8
                        )
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
        workouts[1].exercises[0].id,
    )


@pytest.mark.parametrize("set_type", ["warmup", "working"])
@pytest.mark.asyncio
async def test_add_set_appends_and_persists_without_changing_existing_set(
    db_session: AsyncSession, context, set_type: str
) -> None:
    owner, workout_id, exercise_id, _ = context
    result = await service.add_workout_session_set(
        db_session,
        user_id=owner,
        session_id=workout_id,
        exercise_id=exercise_id,
        data=WorkoutSessionSetCreate(set_type=set_type),
    )
    sets = result.exercises[0].sets
    assert [item.position for item in sets] == [3, 4]
    assert sets[0].planned_reps == 8
    added_id = sets[1].id
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionSet, added_id)
    assert saved.session_exercise_id == exercise_id
    assert saved.set_type == set_type
    assert saved.status == "pending"
    assert saved.planned_reps is None and saved.planned_weight_kg is None
    assert saved.actual_reps is None and saved.actual_weight_kg is None
    assert saved.completed_at is None


@pytest.mark.parametrize(
    "case", ["other_user", "missing_session", "other_exercise", "missing_exercise"]
)
@pytest.mark.asyncio
async def test_add_set_rejects_wrong_resource(
    db_session: AsyncSession, context, case: str
) -> None:
    owner, workout_id, exercise_id, other_id = context
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing_session"}
        else WorkoutSessionExerciseNotFoundError
    )
    with pytest.raises(error):
        await service.add_workout_session_set(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing_session" else workout_id,
            exercise_id=other_id
            if case == "other_exercise"
            else uuid4()
            if case == "missing_exercise"
            else exercise_id,
            data=WorkoutSessionSetCreate(),
        )
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 2
    )


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_add_set_rejects_closed_workout(
    db_session: AsyncSession, context, status: str
) -> None:
    owner, workout_id, exercise_id, _ = context
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.add_workout_session_set(
            db_session,
            user_id=owner,
            session_id=workout_id,
            exercise_id=exercise_id,
            data=WorkoutSessionSetCreate(),
        )
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 2
    )


@pytest.mark.asyncio
async def test_add_set_rolls_back_failed_commit(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    owner, workout_id, exercise_id, _ = context
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.add_workout_session_set(
            db_session,
            user_id=owner,
            session_id=workout_id,
            exercise_id=exercise_id,
            data=WorkoutSessionSetCreate(),
        )
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 2
    )

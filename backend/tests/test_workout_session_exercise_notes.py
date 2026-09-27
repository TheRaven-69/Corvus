from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.schemas.workout_session import WorkoutSessionExerciseUpdate
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession) -> tuple[UUID, UUID, UUID, UUID]:
    user = User(
        email="notes@example.com",
        username="notes",
        first_name="Notes",
        last_name="Owner",
        password_hash="test",
    )
    workouts = [
        WorkoutSession(
            user=user,
            name=name,
            status=status,
            exercises=[
                WorkoutSessionExercise(
                    position=0,
                    notes="Original",
                    exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                    sets=[
                        WorkoutSessionSet(
                            position=0, set_type="working", planned_reps=8
                        )
                    ],
                )
            ],
        )
        for name, status in [("Active", "in_progress"), ("Other", "cancelled")]
    ]
    db_session.add_all(workouts)
    await db_session.commit()
    return (
        user.id,
        workouts[0].id,
        workouts[0].exercises[0].id,
        workouts[1].exercises[0].id,
    )


@pytest.mark.parametrize("notes", ["Повільно", "", None])
@pytest.mark.asyncio
async def test_exercise_notes_persist_without_changing_workout_or_sets(
    db_session: AsyncSession, context: tuple[UUID, UUID, UUID, UUID], notes: str | None
) -> None:
    owner, workout_id, exercise_id, other_id = context
    result = await service.update_workout_session_exercise(
        db_session,
        user_id=owner,
        session_id=workout_id,
        exercise_id=exercise_id,
        data=WorkoutSessionExerciseUpdate(notes=notes),
    )
    assert result.exercises[0].notes == notes
    assert result.notes is None
    assert result.exercises[0].sets[0].planned_reps == 8
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionExercise, exercise_id)
    other = await db_session.get(WorkoutSessionExercise, other_id)
    assert saved is not None and saved.notes == notes
    assert other is not None and other.notes == "Original"


@pytest.mark.parametrize(
    "case", ["other_exercise", "missing_exercise", "other_user", "missing_session"]
)
@pytest.mark.asyncio
async def test_exercise_notes_reject_wrong_resource(
    db_session: AsyncSession, context: tuple[UUID, UUID, UUID, UUID], case: str
) -> None:
    owner, workout_id, exercise_id, other_id = context
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing_session"}
        else WorkoutSessionExerciseNotFoundError
    )
    with pytest.raises(error):
        await service.update_workout_session_exercise(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing_session" else workout_id,
            exercise_id=other_id if case == "other_exercise" else uuid4(),
            data=WorkoutSessionExerciseUpdate(notes="Change"),
        )
    saved = await db_session.get(WorkoutSessionExercise, exercise_id)
    assert saved is not None and saved.notes == "Original"


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_exercise_notes_reject_closed_session(
    db_session: AsyncSession, context: tuple[UUID, UUID, UUID, UUID], status: str
) -> None:
    owner, workout_id, exercise_id, _ = context
    workout = await db_session.get(WorkoutSession, workout_id)
    assert workout is not None
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.update_workout_session_exercise(
            db_session,
            user_id=owner,
            session_id=workout_id,
            exercise_id=exercise_id,
            data=WorkoutSessionExerciseUpdate(notes="Change"),
        )


@pytest.mark.asyncio
async def test_exercise_notes_roll_back_failed_commit(
    db_session: AsyncSession,
    context: tuple[UUID, UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    owner, workout_id, exercise_id, _ = context
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.update_workout_session_exercise(
            db_session,
            user_id=owner,
            session_id=workout_id,
            exercise_id=exercise_id,
            data=WorkoutSessionExerciseUpdate(notes="Change"),
        )
    saved = await db_session.get(WorkoutSessionExercise, exercise_id)
    assert saved is not None and saved.notes == "Original"

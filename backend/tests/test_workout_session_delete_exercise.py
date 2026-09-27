from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionExerciseDeletionNotAllowedError,
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    user = User(
        email="remove@example.com",
        username="remove",
        first_name="Test",
        last_name="Owner",
        password_hash="test",
    )
    catalog = Exercise(code="squat-delete-test", names={"en": "Squat"})
    db_session.add(catalog)
    await db_session.flush()
    workouts = [
        WorkoutSession(
            user=user,
            name=status,
            status=status,
            exercises=[
                WorkoutSessionExercise(
                    position=i,
                    exercise_id=catalog.id,
                    exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                    sets=[
                        WorkoutSessionSet(
                            position=0, set_type="working", planned_reps=8
                        ),
                        WorkoutSessionSet(
                            position=1, set_type="working", status="skipped"
                        ),
                    ],
                )
                for i in range(2)
            ],
        )
        for status in ["in_progress", "cancelled"]
    ]
    db_session.add_all(workouts)
    await db_session.commit()
    return {
        "owner": user.id,
        "workout": workouts[0].id,
        "catalog": catalog.id,
        "exercises": [e.id for e in workouts[0].exercises],
        "sets": [s.id for s in workouts[0].exercises[0].sets],
        "foreign": workouts[1].exercises[0].id,
    }


@pytest.mark.asyncio
async def test_delete_exercise_cascades_sets_preserves_catalog_and_order(
    db_session: AsyncSession, context
) -> None:
    c = context
    result = await service.delete_workout_session_exercise(
        db_session,
        user_id=c["owner"],
        session_id=c["workout"],
        exercise_id=c["exercises"][0],
    )
    assert [e.id for e in result.exercises] == [c["exercises"][1]]
    assert result.exercises[0].position == 1
    assert result.exercises[0].sets[0].planned_reps == 8
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionExercise, c["exercises"][0]) is None
    for set_id in c["sets"]:
        assert await db_session.get(WorkoutSessionSet, set_id) is None
    assert await db_session.get(Exercise, c["catalog"]) is not None
    assert await db_session.get(WorkoutSessionExercise, c["foreign"]) is not None
    result = await service.delete_workout_session_exercise(
        db_session,
        user_id=c["owner"],
        session_id=c["workout"],
        exercise_id=c["exercises"][1],
    )
    assert result.exercises == [] and result.status == "in_progress"


@pytest.mark.asyncio
async def test_delete_exercise_with_completed_set_rejected(
    db_session: AsyncSession, context
) -> None:
    c = context
    item = await db_session.get(WorkoutSessionSet, c["sets"][1])
    item.status = "completed"
    item.actual_reps = 8
    item.completed_at = datetime.now(UTC)
    await db_session.commit()
    with pytest.raises(WorkoutSessionExerciseDeletionNotAllowedError):
        await service.delete_workout_session_exercise(
            db_session,
            user_id=c["owner"],
            session_id=c["workout"],
            exercise_id=c["exercises"][0],
        )
    assert await db_session.get(WorkoutSessionExercise, c["exercises"][0]) is not None
    saved = await db_session.get(WorkoutSessionSet, c["sets"][1])
    assert saved.status == "completed" and saved.actual_reps == 8


@pytest.mark.parametrize(
    "case", ["other_user", "missing_session", "other_exercise", "missing_exercise"]
)
@pytest.mark.asyncio
async def test_delete_exercise_rejects_wrong_resource(
    db_session: AsyncSession, context, case: str
) -> None:
    c = context
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing_session"}
        else WorkoutSessionExerciseNotFoundError
    )
    with pytest.raises(error):
        await service.delete_workout_session_exercise(
            db_session,
            user_id=uuid4() if case == "other_user" else c["owner"],
            session_id=uuid4() if case == "missing_session" else c["workout"],
            exercise_id=c["foreign"]
            if case == "other_exercise"
            else uuid4()
            if case == "missing_exercise"
            else c["exercises"][0],
        )
    assert await db_session.get(WorkoutSessionExercise, c["exercises"][0]) is not None
    assert await db_session.get(WorkoutSessionExercise, c["foreign"]) is not None


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_delete_exercise_rejects_closed_session(
    db_session: AsyncSession, context, status: str
) -> None:
    c = context
    workout = await db_session.get(WorkoutSession, c["workout"])
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.delete_workout_session_exercise(
            db_session,
            user_id=c["owner"],
            session_id=c["workout"],
            exercise_id=c["exercises"][0],
        )
    assert await db_session.get(WorkoutSessionExercise, c["exercises"][0]) is not None


@pytest.mark.asyncio
async def test_delete_exercise_rolls_back_children_on_commit_failure(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    c = context
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.delete_workout_session_exercise(
            db_session,
            user_id=c["owner"],
            session_id=c["workout"],
            exercise_id=c["exercises"][0],
        )
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionExercise, c["exercises"][0]) is not None
    for set_id in c["sets"]:
        assert await db_session.get(WorkoutSessionSet, set_id) is not None

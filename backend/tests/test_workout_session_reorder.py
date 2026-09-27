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
from app.schemas.workout_session import (
    WorkoutSessionExercisesReorder,
    WorkoutSessionRead,
)
from app.services import workout_session as service
from app.services.exceptions import (
    InvalidWorkoutSessionExerciseOrderError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    user = User(
        email="order@example.com",
        username="order",
        first_name="Order",
        last_name="Test",
        password_hash="test",
    )
    workout = WorkoutSession(
        user=user,
        name="Order",
        exercises=[
            WorkoutSessionExercise(
                position=position,
                notes=f"Note {position}",
                exercise_snapshot={"names": {"en": str(position)}, "muscle_groups": []},
                sets=[
                    WorkoutSessionSet(
                        position=0,
                        set_type="working",
                        status="completed",
                        actual_reps=8,
                        actual_weight_kg=20,
                        completed_at=datetime.now(UTC),
                    )
                ],
            )
            for position in [0, 2, 5]
        ],
    )
    other = WorkoutSession(
        user=user,
        name="Other",
        status="cancelled",
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []},
            )
        ],
    )
    db_session.add_all([workout, other])
    await db_session.commit()
    return user.id, workout.id, [e.id for e in workout.exercises], other.exercises[0].id


async def read(db_session: AsyncSession, owner, workout_id):
    workout = await service.get_workout_session(
        db_session, user_id=owner, session_id=workout_id
    )
    return WorkoutSessionRead.model_validate(workout).model_dump(
        exclude={"duration_seconds"}
    )


@pytest.mark.parametrize("order", [[2, 1, 0], [1, 2, 0], [0, 1, 2]])
@pytest.mark.asyncio
async def test_reorder_persists_and_preserves_results(
    db_session: AsyncSession, context, order: list[int]
) -> None:
    owner, workout_id, ids, _ = context
    before = await read(db_session, owner, workout_id)
    desired = [ids[i] for i in order]
    result = await service.reorder_workout_session_exercises(
        db_session,
        user_id=owner,
        session_id=workout_id,
        data=WorkoutSessionExercisesReorder(exercise_ids=desired),
    )
    assert [e.id for e in result.exercises] == desired
    assert [e.position for e in result.exercises] == [0, 1, 2]
    db_session.expunge_all()
    after = await read(db_session, owner, workout_id)
    assert [e["id"] for e in after["exercises"]] == desired
    originals = {e["id"]: e for e in before["exercises"]}
    for position, exercise in enumerate(after["exercises"]):
        assert exercise == {**originals[exercise["id"]], "position": position}
    repeated = await service.reorder_workout_session_exercises(
        db_session,
        user_id=owner,
        session_id=workout_id,
        data=WorkoutSessionExercisesReorder(exercise_ids=desired),
    )
    assert [e.id for e in repeated.exercises] == desired


@pytest.mark.parametrize(
    "case", ["omitted", "extra", "foreign", "unknown", "other_user", "missing_session"]
)
@pytest.mark.asyncio
async def test_reorder_rejects_wrong_resources(
    db_session: AsyncSession, context, case: str
) -> None:
    owner, workout_id, ids, foreign = context
    before = await read(db_session, owner, workout_id)
    requested = (
        ids[:2]
        if case == "omitted"
        else [*ids, uuid4()]
        if case == "extra"
        else [ids[0], ids[1], foreign if case == "foreign" else uuid4()]
        if case in {"foreign", "unknown"}
        else ids
    )
    error = (
        WorkoutSessionNotFoundError
        if case in {"other_user", "missing_session"}
        else InvalidWorkoutSessionExerciseOrderError
    )
    with pytest.raises(error):
        await service.reorder_workout_session_exercises(
            db_session,
            user_id=uuid4() if case == "other_user" else owner,
            session_id=uuid4() if case == "missing_session" else workout_id,
            data=WorkoutSessionExercisesReorder(exercise_ids=requested),
        )
    assert await read(db_session, owner, workout_id) == before


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_reorder_rejects_closed_session(
    db_session: AsyncSession, context, status: str
) -> None:
    owner, workout_id, ids, _ = context
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    before = await read(db_session, owner, workout_id)
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.reorder_workout_session_exercises(
            db_session,
            user_id=owner,
            session_id=workout_id,
            data=WorkoutSessionExercisesReorder(exercise_ids=ids[::-1]),
        )
    assert await read(db_session, owner, workout_id) == before


@pytest.mark.parametrize("failure", ["second_flush", "commit"])
@pytest.mark.asyncio
async def test_reorder_restores_original_positions_on_failure(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    owner, workout_id, ids, _ = context
    before = await read(db_session, owner, workout_id)
    original_flush = db_session.flush
    calls = 0

    async def fail_commit() -> None:
        raise RuntimeError("Save failed")

    async def fail_second_flush(*args, **kwargs) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Save failed")
        await original_flush(*args, **kwargs)

    monkeypatch.setattr(
        db_session,
        "commit" if failure == "commit" else "flush",
        fail_commit if failure == "commit" else fail_second_flush,
    )
    with pytest.raises(RuntimeError, match="Save failed"):
        await service.reorder_workout_session_exercises(
            db_session,
            user_id=owner,
            session_id=workout_id,
            data=WorkoutSessionExercisesReorder(exercise_ids=ids[::-1]),
        )
    db_session.expunge_all()
    assert await read(db_session, owner, workout_id) == before

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    MuscleGroup,
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.schemas.workout_session import WorkoutSessionExerciseCreate, WorkoutSessionRead
from app.services import workout_session as service
from app.services.exceptions import (
    UnavailableExercisesError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def catalog(db_session: AsyncSession) -> dict[str, UUID]:
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="User",
            password_hash="test",
        )
        for name in ["owner", "other"]
    ]
    db_session.add_all(users)
    await db_session.flush()
    group = MuscleGroup(code="core", names={"en": "Core"})
    exercises = [
        Exercise(code="crunch", names={"en": "Crunch"}, muscle_groups=[group]),
        Exercise(owner_user_id=users[0].id, names={"en": "Own"}),
        Exercise(owner_user_id=users[1].id, names={"en": "Private"}),
    ]
    workout = WorkoutSession(user_id=users[0].id, name="Active", exercises=[])
    db_session.add_all([*exercises, workout])
    await db_session.commit()
    return dict(
        zip(
            ["owner", "other", "system", "custom", "private", "session"],
            [users[0].id, users[1].id, *[item.id for item in exercises], workout.id],
            strict=True,
        )
    )


def request(exercise_id: UUID) -> WorkoutSessionExerciseCreate:
    return WorkoutSessionExerciseCreate.model_validate(
        {
            "exercise_id": exercise_id,
            "notes": "Extra",
            "sets": [{"set_type": "warmup"}, {}],
        }
    )


@pytest.mark.parametrize("kind", ["system", "custom"])
@pytest.mark.asyncio
async def test_add_visible_exercise_persists_ordered_unplanned_sets(
    db_session: AsyncSession, catalog: dict[str, UUID], kind: str
) -> None:
    for expected_position in [0, 1]:
        workout = await service.add_workout_session_exercise(
            db_session,
            user_id=catalog["owner"],
            session_id=catalog["session"],
            data=request(catalog[kind]),
        )
        added = workout.exercises[-1]
        assert added.position == expected_position
        assert added.notes == "Extra"
        assert added.exercise_id == catalog[kind]
        assert [item.position for item in added.sets] == [0, 1]
        assert [item.set_type for item in added.sets] == ["warmup", "working"]
        assert all(
            item.planned_reps is None
            and item.planned_weight_kg is None
            and item.actual_reps is None
            and item.actual_weight_kg is None
            and item.status == "pending"
            for item in added.sets
        )
    original_names = dict(added.exercise_snapshot["names"])
    exercise = await db_session.get(Exercise, catalog[kind])
    assert exercise is not None
    exercise.names = {"en": "Renamed"}
    await db_session.commit()
    db_session.expunge_all()
    saved = await service.get_workout_session(
        db_session, user_id=catalog["owner"], session_id=catalog["session"]
    )
    result = WorkoutSessionRead.model_validate(saved)
    assert len(result.exercises) == 2
    assert result.exercises[1].exercise_snapshot.names == original_names
    assert result.exercises[1].exercise_snapshot.muscle_groups == (
        ["core"] if kind == "system" else []
    )


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.asyncio
async def test_add_rejects_private_or_missing_catalog_exercise(
    db_session: AsyncSession, catalog: dict[str, UUID], missing: bool
) -> None:
    with pytest.raises(UnavailableExercisesError):
        await service.add_workout_session_exercise(
            db_session,
            user_id=catalog["owner"],
            session_id=catalog["session"],
            data=request(uuid4() if missing else catalog["private"]),
        )
    assert (
        await db_session.scalar(
            select(func.count()).select_from(WorkoutSessionExercise)
        )
        == 0
    )


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_add_rejects_closed_session(
    db_session: AsyncSession, catalog: dict[str, UUID], status: str
) -> None:
    workout = await db_session.get(WorkoutSession, catalog["session"])
    assert workout is not None
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.add_workout_session_exercise(
            db_session,
            user_id=catalog["owner"],
            session_id=catalog["session"],
            data=request(catalog["system"]),
        )


@pytest.mark.asyncio
async def test_add_rejects_foreign_session(
    db_session: AsyncSession, catalog: dict[str, UUID]
) -> None:
    with pytest.raises(WorkoutSessionNotFoundError):
        await service.add_workout_session_exercise(
            db_session,
            user_id=catalog["other"],
            session_id=catalog["session"],
            data=request(catalog["system"]),
        )


@pytest.mark.asyncio
async def test_add_rolls_back_children_on_commit_failure(
    db_session: AsyncSession, catalog: dict[str, UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.add_workout_session_exercise(
            db_session,
            user_id=catalog["owner"],
            session_id=catalog["session"],
            data=request(catalog["system"]),
        )
    for model in [WorkoutSessionExercise, WorkoutSessionSet]:
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0

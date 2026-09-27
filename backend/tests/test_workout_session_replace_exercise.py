from datetime import UTC, datetime
from uuid import uuid4

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
from app.schemas.workout_session import WorkoutSessionExerciseCreate
from app.services import workout_session as service
from app.services.exceptions import (
    UnavailableExercisesError,
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionExerciseReplacementNotAllowedError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def context(db_session: AsyncSession):
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="Test",
            password_hash="test",
        )
        for name in ["owner", "other"]
    ]
    db_session.add_all(users)
    await db_session.flush()
    catalog = [
        Exercise(code="old", names={"en": "Old"}),
        Exercise(
            code="new",
            names={"en": "New"},
            muscle_groups=[MuscleGroup(code="core", names={"en": "Core"})],
        ),
        Exercise(owner_user_id=users[0].id, names={"en": "Own"}),
        Exercise(owner_user_id=users[1].id, names={"en": "Private"}),
    ]
    db_session.add_all(catalog)
    await db_session.flush()
    exercise = WorkoutSessionExercise(
        position=2,
        exercise_id=catalog[0].id,
        notes="Old note",
        exercise_snapshot={"names": {"en": "Old"}, "muscle_groups": []},
        sets=[
            WorkoutSessionSet(
                position=0,
                set_type="working",
                planned_reps=12,
                actual_reps=6,
                actual_weight_kg=20,
            )
        ],
    )
    foreign = WorkoutSessionExercise(
        position=0, exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []}
    )
    workout = WorkoutSession(user_id=users[0].id, name="Active", exercises=[exercise])
    db_session.add_all(
        [
            workout,
            WorkoutSession(user_id=users[1].id, name="Other", exercises=[foreign]),
        ]
    )
    await db_session.commit()
    return {
        "owner": users[0].id,
        "other": users[1].id,
        "workout": workout.id,
        "exercise": exercise.id,
        "old_set": exercise.sets[0].id,
        "old": catalog[0].id,
        "system": catalog[1].id,
        "custom": catalog[2].id,
        "private": catalog[3].id,
        "foreign": foreign.id,
    }


def payload(exercise_id):
    return WorkoutSessionExerciseCreate.model_validate(
        {"exercise_id": exercise_id, "sets": [{"set_type": "warmup"}, {}]}
    )


@pytest.mark.parametrize("kind", ["system", "custom"])
@pytest.mark.asyncio
async def test_replace_exercise_resets_sets_preserves_identity_and_snapshot(
    db_session: AsyncSession, context, kind: str
) -> None:
    c = context
    result = await service.replace_workout_session_exercise(
        db_session,
        user_id=c["owner"],
        session_id=c["workout"],
        exercise_id=c["exercise"],
        data=payload(c[kind]),
    )
    item = result.exercises[0]
    assert item.id == c["exercise"] and item.position == 2
    assert item.exercise_id == c[kind] and item.notes is None
    expected = {
        "names": {"en": "New" if kind == "system" else "Own"},
        "muscle_groups": ["core"] if kind == "system" else [],
    }
    assert item.exercise_snapshot == expected
    assert [s.position for s in item.sets] == [0, 1]
    assert [s.set_type for s in item.sets] == ["warmup", "working"]
    assert all(
        s.id != c["old_set"]
        and s.status == "pending"
        and s.actual_reps is None
        and s.actual_weight_kg is None
        and s.planned_reps is None
        and s.planned_weight_kg is None
        and s.completed_at is None
        for s in item.sets
    )
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionSet, c["old_set"]) is None
    assert await db_session.get(Exercise, c["old"]) is not None
    replacement = await db_session.get(Exercise, c[kind])
    replacement.names = {"en": "Renamed"}
    await db_session.commit()
    saved = await service.get_workout_session(
        db_session, user_id=c["owner"], session_id=c["workout"]
    )
    assert saved.exercises[0].exercise_snapshot == expected
    assert len(saved.exercises[0].sets) == 2


@pytest.mark.parametrize(
    "case",
    [
        "private",
        "missing_catalog",
        "other_user",
        "missing_session",
        "foreign_exercise",
        "missing_exercise",
        "completed_set",
        "completed",
        "cancelled",
    ],
)
@pytest.mark.asyncio
async def test_replace_exercise_rejects_invalid_operation_without_data_loss(
    db_session: AsyncSession, context, case: str
) -> None:
    c = context
    error = UnavailableExercisesError
    if case in {"other_user", "missing_session"}:
        error = WorkoutSessionNotFoundError
    elif case in {"foreign_exercise", "missing_exercise"}:
        error = WorkoutSessionExerciseNotFoundError
    elif case == "completed_set":
        error = WorkoutSessionExerciseReplacementNotAllowedError
        item = await db_session.get(WorkoutSessionSet, c["old_set"])
        item.status = "completed"
        item.completed_at = datetime.now(UTC)
    elif case in {"completed", "cancelled"}:
        error = WorkoutSessionNotActiveError
        workout = await db_session.get(WorkoutSession, c["workout"])
        workout.status = case
        workout.completed_at = workout.started_at if case == "completed" else None
    await db_session.commit()
    with pytest.raises(error):
        await service.replace_workout_session_exercise(
            db_session,
            user_id=c["other"] if case == "other_user" else c["owner"],
            session_id=uuid4() if case == "missing_session" else c["workout"],
            exercise_id=c["foreign"]
            if case == "foreign_exercise"
            else uuid4()
            if case == "missing_exercise"
            else c["exercise"],
            data=payload(
                c["private"]
                if case == "private"
                else uuid4()
                if case == "missing_catalog"
                else c["system"]
            ),
        )
    saved = await db_session.get(WorkoutSessionExercise, c["exercise"])
    assert saved.exercise_id == c["old"] and saved.notes == "Old note"
    old_set = await db_session.get(WorkoutSessionSet, c["old_set"])
    assert old_set.actual_reps == 6


@pytest.mark.asyncio
async def test_replace_exercise_rolls_back_deleted_sets_on_commit_failure(
    db_session: AsyncSession, context, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail)
    c = context
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.replace_workout_session_exercise(
            db_session,
            user_id=c["owner"],
            session_id=c["workout"],
            exercise_id=c["exercise"],
            data=payload(c["system"]),
        )
    db_session.expunge_all()
    saved = await service.get_workout_session(
        db_session, user_id=c["owner"], session_id=c["workout"]
    )
    item = saved.exercises[0]
    assert item.exercise_id == c["old"] and item.notes == "Old note"
    assert item.exercise_snapshot["names"] == {"en": "Old"}
    assert [s.id for s in item.sets] == [c["old_set"]]
    assert item.sets[0].actual_reps == 6

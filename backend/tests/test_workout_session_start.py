from decimal import Decimal
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
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from app.schemas.workout_session import WorkoutSessionCreate, WorkoutSessionRead
from app.services import workout_session as service
from app.services.exceptions import (
    ActiveWorkoutSessionExistsError,
    InvalidWorkoutTemplateError,
    WorkoutTemplateNotFoundError,
)
from psycopg.errors import UniqueViolation
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_start_translates_psycopg_active_session_conflict(
    db_session: AsyncSession,
    plan: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = UniqueViolation(
        "duplicate active session",
        info={ord("n"): b"uq_workout_sessions_user_in_progress"},
    )
    assert original.sqlstate == "23505"
    assert original.diag.constraint_name == "uq_workout_sessions_user_in_progress"
    failure = IntegrityError("INSERT", {}, original)

    async def fail_commit() -> None:
        raise failure

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(ActiveWorkoutSessionExistsError) as caught:
        await service.start_workout_session(
            db_session,
            user_id=plan[0],
            data=WorkoutSessionCreate(template_id=plan[1]),
        )
    assert caught.value.__cause__ is failure
    await assert_no_sessions(db_session)


@pytest.mark.parametrize(
    ("sqlstate", "constraint", "translate"),
    [
        ("23505", "uq_workout_sessions_user_in_progress", True),
        ("23505", "another_unique_constraint", False),
        ("23503", "uq_workout_sessions_user_in_progress", False),
        (None, None, False),
    ],
)
@pytest.mark.asyncio
async def test_start_translates_only_active_session_unique_conflict(
    db_session: AsyncSession,
    plan: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
    sqlstate: str | None,
    constraint: str | None,
    translate: bool,
) -> None:
    class DatabaseError(Exception):
        def __init__(self) -> None:
            self.sqlstate = sqlstate
            self.constraint_name = constraint

    original = Exception("Driver wrapper")
    if sqlstate is not None:
        original.__cause__ = DatabaseError()
    failure = IntegrityError("INSERT", {}, original)

    async def fail_commit() -> None:
        raise failure

    monkeypatch.setattr(db_session, "commit", fail_commit)
    expected = ActiveWorkoutSessionExistsError if translate else IntegrityError
    with pytest.raises(expected) as caught:
        await service.start_workout_session(
            db_session,
            user_id=plan[0],
            data=WorkoutSessionCreate(template_id=plan[1]),
        )
    if translate:
        assert caught.value.__cause__ is failure
    else:
        assert caught.value is failure
    await assert_no_sessions(db_session)


@pytest_asyncio.fixture
async def plan(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    user = User(
        email="start@example.com",
        username="start_owner",
        first_name="Start",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )
    exercise = Exercise(
        code="squat",
        names={"en": "Squat", "uk": "Присідання"},
        muscle_groups=[MuscleGroup(code="quadriceps", names={"en": "Quadriceps"})],
    )
    template = WorkoutTemplate(
        user=user,
        name="Leg day",
        exercises=[
            WorkoutTemplateExercise(
                exercise=exercise,
                position=0,
                notes="Slow descent",
                sets=[
                    WorkoutTemplateSet(
                        position=1,
                        set_type="working",
                        target_reps=8,
                        target_weight_kg=Decimal("60.50"),
                    ),
                    WorkoutTemplateSet(position=0, set_type="warmup", target_reps=12),
                ],
            )
        ],
    )
    db_session.add(template)
    await db_session.commit()
    ids = user.id, template.id, exercise.id
    db_session.expunge_all()
    return ids


async def assert_no_sessions(session: AsyncSession) -> None:
    for model in [WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet]:
        assert await session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.asyncio
async def test_start_copies_and_commits_independent_plan(
    db_session: AsyncSession, plan: tuple[UUID, UUID, UUID]
) -> None:
    owner_id, template_id, exercise_id = plan
    workout = await service.start_workout_session(
        db_session, user_id=owner_id, data=WorkoutSessionCreate(template_id=template_id)
    )
    result = WorkoutSessionRead.model_validate(workout)
    assert result.name == "Leg day"
    assert result.template_id == template_id
    assert result.status == "in_progress"
    assert result.started_at is not None and result.completed_at is None
    item = result.exercises[0]
    assert item.notes == "Slow descent"
    assert item.exercise_id == exercise_id
    assert item.exercise_snapshot.names == {"en": "Squat", "uk": "Присідання"}
    assert item.exercise_snapshot.muscle_groups == ["quadriceps"]
    assert [entry.position for entry in item.sets] == [0, 1]
    assert [entry.planned_reps for entry in item.sets] == [12, 8]
    assert [entry.planned_weight_kg for entry in item.sets] == [None, Decimal("60.50")]
    assert all(
        entry.actual_reps is None
        and entry.actual_weight_kg is None
        and entry.status == "pending"
        for entry in item.sets
    )
    workout_id = workout.id
    # Rolling back a later read transaction must not undo the service's commit.
    await db_session.rollback()
    template = await db_session.get(WorkoutTemplate, template_id)
    exercise = await db_session.get(Exercise, exercise_id)
    assert template is not None and exercise is not None
    template.name = "Changed plan"
    exercise.names = {"en": "Renamed"}
    target = await db_session.scalar(
        select(WorkoutTemplateSet).where(WorkoutTemplateSet.position == 1)
    )
    assert target is not None
    target.target_reps = 20
    await db_session.commit()
    db_session.expunge_all()
    saved = await service.get_workout_session(
        db_session, user_id=owner_id, session_id=workout_id
    )
    assert saved.name == "Leg day"
    assert saved.exercises[0].exercise_snapshot["names"]["en"] == "Squat"
    assert saved.exercises[0].sets[1].planned_reps == 8


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.asyncio
async def test_start_rejects_private_or_missing_template(
    db_session: AsyncSession, plan: tuple[UUID, UUID, UUID], missing: bool
) -> None:
    owner_id, template_id, _ = plan
    with pytest.raises(WorkoutTemplateNotFoundError):
        await service.start_workout_session(
            db_session,
            user_id=owner_id if missing else uuid4(),
            data=WorkoutSessionCreate(template_id=uuid4() if missing else template_id),
        )
    await assert_no_sessions(db_session)


@pytest.mark.parametrize("empty_exercises", [False, True])
@pytest.mark.asyncio
async def test_start_rejects_empty_template_structure(
    db_session: AsyncSession, plan: tuple[UUID, UUID, UUID], empty_exercises: bool
) -> None:
    owner_id, _, exercise_id = plan
    template = WorkoutTemplate(
        user_id=owner_id,
        name="Empty",
        exercises=[]
        if empty_exercises
        else [WorkoutTemplateExercise(exercise_id=exercise_id, position=0, sets=[])],
    )
    db_session.add(template)
    await db_session.commit()
    request = WorkoutSessionCreate(template_id=template.id)
    with pytest.raises(InvalidWorkoutTemplateError):
        await service.start_workout_session(db_session, user_id=owner_id, data=request)
    await assert_no_sessions(db_session)


@pytest.mark.asyncio
async def test_start_rejects_existing_active_session(
    db_session: AsyncSession, plan: tuple[UUID, UUID, UUID]
) -> None:
    owner_id, template_id, _ = plan
    request = WorkoutSessionCreate(template_id=template_id)
    first = await service.start_workout_session(
        db_session, user_id=owner_id, data=request
    )
    first_id = first.id
    with pytest.raises(ActiveWorkoutSessionExistsError):
        await service.start_workout_session(db_session, user_id=owner_id, data=request)
    assert list(await db_session.scalars(select(WorkoutSession.id))) == [first_id]
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 2
    )


@pytest.mark.asyncio
async def test_start_rolls_back_tree_when_commit_fails(
    db_session: AsyncSession,
    plan: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_commit() -> None:
        raise RuntimeError("Simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        await service.start_workout_session(
            db_session, user_id=plan[0], data=WorkoutSessionCreate(template_id=plan[1])
        )
    await assert_no_sessions(db_session)
    assert await db_session.get(WorkoutTemplate, plan[1]) is not None

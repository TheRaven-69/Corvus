from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.db.models import (
    Exercise,
    MuscleGroup,
    User,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from app.repositories import workout_template as workout_template_repository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def build_user(suffix: str) -> User:
    return User(
        email=f"template-{suffix}@example.com",
        username=f"template_{suffix}",
        first_name="Template",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )


def build_system_exercise(code: str, name: str) -> Exercise:
    muscle_group = MuscleGroup(
        code=f"{code}_muscle",
        names={"en": "Target muscle"},
    )
    return Exercise(
        owner_user_id=None,
        code=code,
        names={"en": name},
        muscle_groups=[muscle_group],
    )


def build_template_exercise(
    exercise: Exercise,
    *,
    reps: int = 8,
) -> WorkoutTemplateExercise:
    return WorkoutTemplateExercise(
        exercise=exercise,
        position=0,
        notes=None,
        sets=[
            WorkoutTemplateSet(
                position=0,
                set_type="working",
                target_reps=reps,
                target_weight_kg=Decimal("50.00"),
            )
        ],
    )


@pytest.mark.asyncio
async def test_create_and_get_workout_template_loads_complete_owned_aggregate(
    db_session: AsyncSession,
) -> None:
    owner = build_user("owner")
    other_user = build_user("other")
    exercise = build_system_exercise("bench_press", "Bench press")
    db_session.add_all([owner, other_user, exercise])
    await db_session.flush()

    template = await workout_template_repository.create_workout_template(
        db_session,
        user_id=owner.id,
        name="Push day",
        description="Chest and triceps",
        exercises=[build_template_exercise(exercise)],
    )
    await db_session.commit()

    loaded = await workout_template_repository.get_workout_template_by_id(
        db_session,
        template_id=template.id,
        user_id=owner.id,
    )
    hidden_from_other_user = (
        await workout_template_repository.get_workout_template_by_id(
            db_session,
            template_id=template.id,
            user_id=other_user.id,
        )
    )

    assert loaded is not None
    assert loaded.exercises[0].exercise.names["en"] == "Bench press"
    assert loaded.exercises[0].exercise.muscle_groups[0].code == "bench_press_muscle"
    assert loaded.exercises[0].sets[0].target_reps == 8
    assert hidden_from_other_user is None


@pytest.mark.asyncio
async def test_list_workout_templates_filters_owner_and_orders_newest_first(
    db_session: AsyncSession,
) -> None:
    owner = build_user("owner")
    other_user = build_user("other")
    now = datetime.now(UTC)
    oldest = WorkoutTemplate(
        user=owner,
        name="Oldest",
        created_at=now - timedelta(days=1),
    )
    newest = WorkoutTemplate(
        user=owner,
        name="Newest",
        created_at=now,
    )
    other_template = WorkoutTemplate(
        user=other_user,
        name="Private",
        created_at=now + timedelta(days=1),
    )
    db_session.add_all([oldest, newest, other_template])
    await db_session.flush()

    templates = await workout_template_repository.list_workout_templates(
        db_session,
        user_id=owner.id,
    )

    assert [template.name for template in templates] == ["Newest", "Oldest"]


@pytest.mark.asyncio
async def test_replace_workout_template_exercises_reuses_positions_safely(
    db_session: AsyncSession,
) -> None:
    owner = build_user("owner")
    old_exercise = build_system_exercise("squat", "Squat")
    new_exercise = build_system_exercise("deadlift", "Deadlift")
    template = WorkoutTemplate(
        user=owner,
        name="Leg day",
        exercises=[build_template_exercise(old_exercise, reps=5)],
    )
    db_session.add_all([new_exercise, template])
    await db_session.flush()
    old_template_exercise_id = template.exercises[0].id
    old_set_id = template.exercises[0].sets[0].id

    await workout_template_repository.replace_workout_template_exercises(
        db_session,
        template=template,
        exercises=[
            WorkoutTemplateExercise(
                exercise_id=new_exercise.id,
                position=0,
                notes=None,
                sets=[
                    WorkoutTemplateSet(
                        position=0,
                        set_type="working",
                        target_reps=3,
                        target_weight_kg=Decimal("50.00"),
                    )
                ],
            )
        ],
    )

    assert template.exercises[0].position == 0
    assert template.exercises[0].exercise_id == new_exercise.id
    assert template.exercises[0].sets[0].target_reps == 3
    assert (
        await db_session.get(WorkoutTemplateExercise, old_template_exercise_id) is None
    )
    assert await db_session.get(WorkoutTemplateSet, old_set_id) is None


@pytest.mark.asyncio
async def test_update_workout_template_changes_details_and_timestamp(
    db_session: AsyncSession,
) -> None:
    old_timestamp = datetime.now(UTC) - timedelta(days=1)
    template = WorkoutTemplate(
        user=build_user("owner"),
        name="Old name",
        description="Old description",
        updated_at=old_timestamp,
    )
    db_session.add(template)
    await db_session.flush()

    updated = await workout_template_repository.update_workout_template(
        db_session,
        template=template,
        name="New name",
        description=None,
    )

    assert updated.name == "New name"
    assert updated.description is None
    assert updated.updated_at > old_timestamp


@pytest.mark.asyncio
async def test_delete_workout_template_removes_children_but_keeps_exercise(
    db_session: AsyncSession,
) -> None:
    exercise = build_system_exercise("squat", "Squat")
    template = WorkoutTemplate(
        user=build_user("owner"),
        name="Temporary",
        exercises=[build_template_exercise(exercise)],
    )
    db_session.add(template)
    await db_session.flush()
    template_id = template.id
    exercise_id = exercise.id

    await workout_template_repository.delete_workout_template(
        db_session,
        template=template,
    )

    template_exercise_count = await db_session.scalar(
        select(func.count()).select_from(WorkoutTemplateExercise)
    )
    template_set_count = await db_session.scalar(
        select(func.count()).select_from(WorkoutTemplateSet)
    )

    assert await db_session.get(WorkoutTemplate, template_id) is None
    assert template_exercise_count == 0
    assert template_set_count == 0
    assert await db_session.get(Exercise, exercise_id) is not None

from decimal import Decimal

import pytest
from app.db.models import (
    Exercise,
    User,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


def build_user() -> User:
    return User(
        email="template-owner@example.com",
        username="template_owner",
        first_name="Template",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )


def build_system_exercise(code: str, name: str) -> Exercise:
    return Exercise(
        owner_user_id=None,
        code=code,
        names={"en": name},
    )


@pytest.mark.asyncio
async def test_saving_workout_template_persists_nested_structure(
    db_session: AsyncSession,
) -> None:
    template = WorkoutTemplate(
        user=build_user(),
        name="Strength day",
        description="Main compound lifts",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise(
                    "bench_press",
                    "Bench press",
                ),
                position=0,
                notes="Control the eccentric",
                sets=[
                    WorkoutTemplateSet(
                        position=0,
                        set_type="warmup",
                        target_reps=10,
                        target_weight_kg=Decimal("20.00"),
                    ),
                    WorkoutTemplateSet(
                        position=1,
                        set_type="working",
                        target_reps=5,
                        target_weight_kg=Decimal("60.00"),
                    ),
                ],
            )
        ],
    )

    db_session.add(template)
    await db_session.commit()

    template_exercise = template.exercises[0]

    assert template.id is not None
    assert template_exercise.template_id == template.id
    assert template_exercise.exercise_id == template_exercise.exercise.id
    assert template_exercise.sets[0].template_exercise_id == template_exercise.id
    assert template_exercise.sets[1].template_exercise_id == template_exercise.id


@pytest.mark.asyncio
async def test_workout_template_loads_exercises_and_sets_in_position_order(
    db_session: AsyncSession,
) -> None:
    template = WorkoutTemplate(
        user=build_user(),
        name="Ordered workout",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise("bench_press", "Bench press"),
                position=1,
                sets=[
                    WorkoutTemplateSet(
                        position=1,
                        set_type="working",
                        target_reps=5,
                    ),
                    WorkoutTemplateSet(
                        position=0,
                        set_type="warmup",
                        target_reps=10,
                    ),
                ],
            ),
            WorkoutTemplateExercise(
                exercise=build_system_exercise("squat", "Squat"),
                position=0,
                sets=[
                    WorkoutTemplateSet(
                        position=0,
                        set_type="working",
                        target_reps=5,
                    )
                ],
            ),
        ],
    )
    db_session.add(template)
    await db_session.commit()

    saved_template = await db_session.scalar(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template.id)
        .options(
            selectinload(WorkoutTemplate.exercises).selectinload(
                WorkoutTemplateExercise.sets
            )
        )
        .execution_options(populate_existing=True)
    )

    assert saved_template is not None
    assert [item.position for item in saved_template.exercises] == [0, 1]
    assert [item.position for item in saved_template.exercises[1].sets] == [0, 1]


@pytest.mark.asyncio
async def test_workout_template_rejects_duplicate_exercise_positions(
    db_session: AsyncSession,
) -> None:
    template = WorkoutTemplate(
        user=build_user(),
        name="Invalid exercise order",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise("squat", "Squat"),
                position=0,
            ),
            WorkoutTemplateExercise(
                exercise=build_system_exercise("deadlift", "Deadlift"),
                position=0,
            ),
        ],
    )
    db_session.add(template)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_workout_template_rejects_duplicate_set_positions(
    db_session: AsyncSession,
) -> None:
    template = WorkoutTemplate(
        user=build_user(),
        name="Invalid set order",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise("squat", "Squat"),
                position=0,
                sets=[
                    WorkoutTemplateSet(
                        position=0,
                        set_type="warmup",
                        target_reps=8,
                    ),
                    WorkoutTemplateSet(
                        position=0,
                        set_type="working",
                        target_reps=5,
                    ),
                ],
            )
        ],
    )
    db_session.add(template)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.parametrize(
    "invalid_values",
    [
        {"position": -1},
        {"set_type": "drop"},
        {"target_reps": 0},
        {"target_weight_kg": Decimal("-0.01")},
    ],
)
@pytest.mark.asyncio
async def test_workout_template_set_rejects_invalid_values(
    db_session: AsyncSession,
    invalid_values: dict[str, object],
) -> None:
    set_values: dict[str, object] = {
        "position": 0,
        "set_type": "working",
        "target_reps": 5,
        "target_weight_kg": Decimal("20.00"),
    }
    set_values.update(invalid_values)
    template = WorkoutTemplate(
        user=build_user(),
        name="Invalid target",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise("squat", "Squat"),
                position=0,
                sets=[WorkoutTemplateSet(**set_values)],
            )
        ],
    )
    db_session.add(template)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_workout_template_rejects_negative_exercise_position(
    db_session: AsyncSession,
) -> None:
    template = WorkoutTemplate(
        user=build_user(),
        name="Invalid exercise position",
        exercises=[
            WorkoutTemplateExercise(
                exercise=build_system_exercise("squat", "Squat"),
                position=-1,
            )
        ],
    )
    db_session.add(template)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_deleting_workout_template_cascades_to_children_only(
    db_session: AsyncSession,
) -> None:
    exercise = build_system_exercise("squat", "Squat")
    template = WorkoutTemplate(
        user=build_user(),
        name="Temporary template",
        exercises=[
            WorkoutTemplateExercise(
                exercise=exercise,
                position=0,
                sets=[
                    WorkoutTemplateSet(
                        position=0,
                        set_type="working",
                        target_reps=5,
                    )
                ],
            )
        ],
    )
    db_session.add(template)
    await db_session.commit()

    await db_session.delete(template)
    await db_session.commit()

    template_exercise_count = await db_session.scalar(
        select(func.count()).select_from(WorkoutTemplateExercise)
    )
    template_set_count = await db_session.scalar(
        select(func.count()).select_from(WorkoutTemplateSet)
    )
    saved_exercise = await db_session.get(Exercise, exercise.id)

    assert template_exercise_count == 0
    assert template_set_count == 0
    assert saved_exercise is not None

import pytest
from app.db.models import Exercise, MuscleGroup, User
from app.schemas.exercise import ExerciseCreate
from app.services import exercise as exercise_service
from app.services.exercise import UnknownMuscleGroupsError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_custom_exercise_persists_data(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="owner@example.com",
        username="owner",
        first_name="Exercise",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )
    chest = MuscleGroup(
        code="chest",
        names={"en": "Chest", "uk": "Груди"},
    )
    triceps = MuscleGroup(
        code="triceps",
        names={"en": "Triceps", "uk": "Трицепс"},
    )

    db_session.add_all([user, chest, triceps])
    await db_session.commit()

    created_exercise = await exercise_service.create_custom_exercise(
        db_session,
        user_id=user.id,
        data=ExerciseCreate(
            name="  Жим гантелей  ",
            locale="uk",
            muscle_group_codes=["chest", "triceps"],
        ),
    )

    stored_exercise = (
        await db_session.scalars(
            select(Exercise).where(
                Exercise.id == created_exercise.id,
            )
        )
    ).one()

    assert stored_exercise.owner_user_id == user.id
    assert stored_exercise.code is None
    assert stored_exercise.names == {
        "uk": "Жим гантелей",
    }
    assert {group.code for group in stored_exercise.muscle_groups} == {
        "chest",
        "triceps",
    }


@pytest.mark.asyncio
async def test_create_custom_exercise_rejects_unknown_groups(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="owner@example.com",
        username="owner",
        first_name="Exercise",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )
    chest = MuscleGroup(
        code="chest",
        names={"en": "Chest", "uk": "Груди"},
    )

    db_session.add_all([user, chest])
    await db_session.commit()

    with pytest.raises(
        UnknownMuscleGroupsError,
    ) as error_info:
        await exercise_service.create_custom_exercise(
            db_session,
            user_id=user.id,
            data=ExerciseCreate(
                name="Політ",
                locale="uk",
                muscle_group_codes=["chest", "wings"],
            ),
        )

    stored_exercises = (
        await db_session.scalars(
            select(Exercise),
        )
    ).all()

    assert error_info.value.codes == ["wings"]
    assert stored_exercises == []


@pytest.mark.asyncio
async def test_list_visible_exercises_hides_other_users_exercises(
    db_session: AsyncSession,
) -> None:
    current_user = User(
        email="current@example.com",
        username="current",
        first_name="Current",
        last_name="User",
        password_hash="not-a-real-hash",
    )
    other_user = User(
        email="other@example.com",
        username="other",
        first_name="Other",
        last_name="User",
        password_hash="not-a-real-hash",
    )
    chest = MuscleGroup(
        code="chest",
        names={"en": "Chest", "uk": "Груди"},
    )

    system_exercise = Exercise(
        code="barbell_bench_press",
        names={
            "en": "Barbell bench press",
            "uk": "Жим штанги лежачи",
        },
        muscle_groups=[chest],
    )
    own_exercise = Exercise(
        owner=current_user,
        code=None,
        names={"uk": "Моя вправа"},
        muscle_groups=[chest],
    )
    other_users_exercise = Exercise(
        owner=other_user,
        code=None,
        names={"uk": "Чужа вправа"},
        muscle_groups=[chest],
    )

    db_session.add_all(
        [
            current_user,
            other_user,
            chest,
            system_exercise,
            own_exercise,
            other_users_exercise,
        ]
    )
    await db_session.commit()

    visible_exercises = await exercise_service.list_visible_exercises(
        db_session,
        current_user.id,
    )

    visible_ids = {exercise.id for exercise in visible_exercises}

    assert visible_ids == {
        system_exercise.id,
        own_exercise.id,
    }
    assert other_users_exercise.id not in visible_ids

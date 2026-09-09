from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    MuscleGroup,
    User,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateSet,
)
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateExerciseCreate,
    WorkoutTemplateRead,
    WorkoutTemplateSetCreate,
    WorkoutTemplateUpdate,
)
from app.services import workout_template as service
from app.services.exceptions import (
    UnavailableExercisesError,
    WorkoutTemplateNotFoundError,
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
            last_name="Tester",
            password_hash="not-a-real-hash",
        )
        for name in ("owner", "other")
    ]
    group = MuscleGroup(code="chest", names={"en": "Chest"})
    exercises = [
        Exercise(code="bench", names={"en": "Bench"}, muscle_groups=[group]),
        Exercise(owner=users[0], names={"en": "Own"}, muscle_groups=[group]),
        Exercise(owner=users[1], names={"en": "Private"}, muscle_groups=[group]),
    ]
    db_session.add_all([*users, *exercises])
    await db_session.commit()
    return dict(
        zip(
            ("owner", "other", "system", "own", "foreign"),
            [item.id for item in [*users, *exercises]],
            strict=True,
        )
    )


@pytest_asyncio.fixture
async def reader(db_session: AsyncSession) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(bind=db_session.bind, expire_on_commit=False) as session:
        yield session


def exercise_data(
    exercise_id: UUID, position: int = 0
) -> WorkoutTemplateExerciseCreate:
    return WorkoutTemplateExerciseCreate(
        exercise_id=exercise_id,
        position=position,
        notes="Controlled tempo",
        sets=[
            WorkoutTemplateSetCreate(
                position=1,
                set_type="working",
                target_reps=8,
                target_weight_kg=Decimal("42.50"),
            ),
            WorkoutTemplateSetCreate(position=0, set_type="warmup", target_reps=10),
        ],
    )


async def create_template(
    session: AsyncSession, catalog: dict[str, UUID]
) -> WorkoutTemplate:
    return await service.create_workout_template(
        session,
        user_id=catalog["owner"],
        data=WorkoutTemplateCreate(
            name="Push day",
            description="Original description",
            exercises=[exercise_data(catalog["system"])],
        ),
    )


@pytest.mark.asyncio
async def test_create_commits_ordered_serializable_template(
    db_session: AsyncSession,
    reader: AsyncSession,
    catalog: dict[str, UUID],
) -> None:
    template = await service.create_workout_template(
        db_session,
        user_id=catalog["owner"],
        data=WorkoutTemplateCreate(
            name="  Push day  ",
            exercises=[
                exercise_data(catalog["own"], 1),
                exercise_data(catalog["system"], 0),
            ],
        ),
    )
    response = WorkoutTemplateRead.model_validate(template)
    assert response.name == "Push day"
    assert [item.position for item in response.exercises] == [0, 1]
    assert [item.position for item in response.exercises[0].sets] == [0, 1]
    assert response.exercises[0].exercise.muscle_groups[0].code == "chest"
    assert response.exercises[0].sets[1].target_weight_kg == Decimal("42.50")
    stored = await service.get_workout_template(
        reader,
        user_id=catalog["owner"],
        template_id=template.id,
    )
    assert WorkoutTemplateRead.model_validate(stored) == response


@pytest.mark.parametrize("unavailable", ["foreign", "missing"])
@pytest.mark.asyncio
async def test_create_rejects_unavailable_exercises_without_partial_writes(
    db_session: AsyncSession,
    catalog: dict[str, UUID],
    unavailable: str,
) -> None:
    bad_id = catalog["foreign"] if unavailable == "foreign" else uuid4()
    with pytest.raises(UnavailableExercisesError) as error:
        await service.create_workout_template(
            db_session,
            user_id=catalog["owner"],
            data=WorkoutTemplateCreate(
                name="Invalid",
                exercises=[exercise_data(catalog["system"]), exercise_data(bad_id, 1)],
            ),
        )
    assert error.value.exercise_ids == {bad_id}
    for model in (WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("operation", ["get", "update", "delete"])
@pytest.mark.parametrize("target", ["foreign", "missing"])
@pytest.mark.asyncio
async def test_private_and_missing_templates_are_not_found(
    db_session: AsyncSession,
    catalog: dict[str, UUID],
    operation: str,
    target: str,
) -> None:
    template = await create_template(db_session, catalog)
    saved_id = template.id
    template_id = saved_id if target == "foreign" else uuid4()
    with pytest.raises(WorkoutTemplateNotFoundError):
        if operation == "update":
            await service.update_workout_template(
                db_session,
                user_id=catalog["other"],
                template_id=template_id,
                data=WorkoutTemplateUpdate(name="Hacked"),
            )
        elif operation == "delete":
            await service.delete_workout_template(
                db_session, user_id=catalog["other"], template_id=template_id
            )
        else:
            await service.get_workout_template(
                db_session, user_id=catalog["other"], template_id=template_id
            )
    stored = await service.get_workout_template(
        db_session, user_id=catalog["owner"], template_id=saved_id
    )
    assert stored.name == "Push day"


@pytest.mark.asyncio
async def test_list_returns_only_owned_templates(
    db_session: AsyncSession,
    catalog: dict[str, UUID],
) -> None:
    assert (
        await service.list_workout_templates(db_session, user_id=catalog["owner"]) == []
    )
    template = await create_template(db_session, catalog)
    assert (
        await service.list_workout_templates(db_session, user_id=catalog["other"]) == []
    )
    result = await service.list_workout_templates(db_session, user_id=catalog["owner"])
    assert [item.id for item in result] == [template.id]


@pytest.mark.parametrize(
    ("payload", "name", "description"),
    [
        ({"name": "New"}, "New", "Original description"),
        ({"description": None}, "Push day", None),
        ({"description": "New description"}, "Push day", "New description"),
    ],
)
@pytest.mark.asyncio
async def test_patch_preserves_omitted_fields_and_children(
    db_session: AsyncSession,
    reader: AsyncSession,
    catalog: dict[str, UUID],
    payload: dict[str, object],
    name: str,
    description: str | None,
) -> None:
    template = await create_template(db_session, catalog)
    child_id = template.exercises[0].id
    updated = await service.update_workout_template(
        db_session,
        user_id=catalog["owner"],
        template_id=template.id,
        data=WorkoutTemplateUpdate.model_validate(payload),
    )
    assert (updated.name, updated.description) == (name, description)
    stored = await service.get_workout_template(
        reader, user_id=catalog["owner"], template_id=updated.id
    )
    assert (stored.name, stored.description) == (name, description)
    assert stored.exercises[0].id == child_id


@pytest.mark.asyncio
async def test_patch_replaces_children_and_returns_loaded_response(
    db_session: AsyncSession,
    reader: AsyncSession,
    catalog: dict[str, UUID],
) -> None:
    template = await create_template(db_session, catalog)
    old_child_id = template.exercises[0].id
    old_set_ids = [item.id for item in template.exercises[0].sets]
    updated = await service.update_workout_template(
        db_session,
        user_id=catalog["owner"],
        template_id=template.id,
        data=WorkoutTemplateUpdate(exercises=[exercise_data(catalog["own"])]),
    )
    response = WorkoutTemplateRead.model_validate(updated)
    assert response.exercises[0].exercise.names == {"en": "Own"}
    assert response.name == "Push day"
    assert response.description == "Original description"
    stored = await service.get_workout_template(
        reader, user_id=catalog["owner"], template_id=updated.id
    )
    assert WorkoutTemplateRead.model_validate(stored) == response
    assert await reader.get(WorkoutTemplateExercise, old_child_id) is None
    for set_id in old_set_ids:
        assert await reader.get(WorkoutTemplateSet, set_id) is None


@pytest.mark.asyncio
async def test_patch_unavailable_exercise_preserves_original_template(
    db_session: AsyncSession,
    catalog: dict[str, UUID],
) -> None:
    template = await create_template(db_session, catalog)
    before = WorkoutTemplateRead.model_validate(template)
    with pytest.raises(UnavailableExercisesError):
        await service.update_workout_template(
            db_session,
            user_id=catalog["owner"],
            template_id=before.id,
            data=WorkoutTemplateUpdate(
                name="Changed", exercises=[exercise_data(catalog["foreign"])]
            ),
        )
    stored = await service.get_workout_template(
        db_session, user_id=catalog["owner"], template_id=before.id
    )
    assert WorkoutTemplateRead.model_validate(stored) == before


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.asyncio
async def test_commit_failure_rolls_back_all_template_changes(
    db_session: AsyncSession,
    reader: AsyncSession,
    catalog: dict[str, UUID],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    template = await create_template(db_session, catalog)
    before = WorkoutTemplateRead.model_validate(template)

    async def fail_commit() -> None:
        raise RuntimeError("Simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        if operation == "create":
            await create_template(db_session, catalog)
        elif operation == "update":
            await service.update_workout_template(
                db_session,
                user_id=catalog["owner"],
                template_id=before.id,
                data=WorkoutTemplateUpdate(
                    name="Changed", exercises=[exercise_data(catalog["own"])]
                ),
            )
        else:
            await service.delete_workout_template(
                db_session, user_id=catalog["owner"], template_id=before.id
            )
    stored = await service.get_workout_template(
        reader, user_id=catalog["owner"], template_id=before.id
    )
    assert WorkoutTemplateRead.model_validate(stored) == before
    for model, expected in (
        (WorkoutTemplate, 1),
        (WorkoutTemplateExercise, 1),
        (WorkoutTemplateSet, 2),
    ):
        assert await reader.scalar(select(func.count()).select_from(model)) == expected


@pytest.mark.asyncio
async def test_delete_commits_cascade_but_preserves_catalog(
    db_session: AsyncSession,
    reader: AsyncSession,
    catalog: dict[str, UUID],
) -> None:
    template = await create_template(db_session, catalog)
    result = await service.delete_workout_template(
        db_session, user_id=catalog["owner"], template_id=template.id
    )
    assert result is None
    for model in (WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet):
        assert await reader.scalar(select(func.count()).select_from(model)) == 0
    assert await reader.get(Exercise, catalog["system"]) is not None

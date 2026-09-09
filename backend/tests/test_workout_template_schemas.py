from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateRead,
    WorkoutTemplateSetCreate,
    WorkoutTemplateUpdate,
)
from pydantic import ValidationError


def _valid_set(*, position: int = 0) -> dict[str, object]:
    return {
        "position": position,
        "set_type": "working",
        "target_reps": 8,
        "target_weight_kg": "82.50",
    }


def _valid_exercise(*, position: int = 0) -> dict[str, object]:
    return {
        "exercise_id": uuid4(),
        "position": position,
        "notes": None,
        "sets": [_valid_set()],
    }


def _valid_template() -> dict[str, object]:
    return {
        "name": "  Push day  ",
        "description": "Chest and triceps",
        "exercises": [_valid_exercise()],
    }


def test_workout_template_create_accepts_and_normalizes_nested_data() -> None:
    template = WorkoutTemplateCreate.model_validate(_valid_template())

    assert template.name == "Push day"
    assert template.exercises[0].position == 0
    assert template.exercises[0].sets[0].target_weight_kg == Decimal("82.50")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("position", -1),
        ("set_type", "drop"),
        ("target_reps", 0),
        ("target_weight_kg", "-0.01"),
        ("target_weight_kg", "1234567.89"),
        ("target_weight_kg", "82.501"),
    ],
)
def test_workout_template_set_create_rejects_invalid_data(
    field: str,
    value: object,
) -> None:
    data = _valid_set()
    data[field] = value

    with pytest.raises(ValidationError):
        WorkoutTemplateSetCreate.model_validate(data)


@pytest.mark.parametrize(
    "exercises",
    [
        [],
        [{**_valid_exercise(), "sets": []}],
        [
            {
                **_valid_exercise(),
                "sets": [_valid_set(position=0), _valid_set(position=0)],
            }
        ],
        [_valid_exercise(position=0), _valid_exercise(position=0)],
    ],
)
def test_workout_template_create_rejects_invalid_exercise_structure(
    exercises: list[dict[str, object]],
) -> None:
    data = _valid_template()
    data["exercises"] = exercises

    with pytest.raises(ValidationError):
        WorkoutTemplateCreate.model_validate(data)


def test_workout_template_create_rejects_blank_name() -> None:
    data = _valid_template()
    data["name"] = "   "

    with pytest.raises(ValidationError):
        WorkoutTemplateCreate.model_validate(data)


def test_workout_template_update_accepts_partial_fields() -> None:
    update = WorkoutTemplateUpdate.model_validate({"name": "  Pull day  "})

    assert update.name == "Pull day"
    assert update.model_dump(exclude_unset=True) == {"name": "Pull day"}


def test_workout_template_update_allows_clearing_description() -> None:
    update = WorkoutTemplateUpdate.model_validate({"description": None})

    assert update.model_dump(exclude_unset=True) == {"description": None}


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"name": None},
        {"name": "   "},
        {"exercises": None},
        {"exercises": []},
        {"exercises": [_valid_exercise(position=0), _valid_exercise(position=0)]},
    ],
)
def test_workout_template_update_rejects_invalid_data(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkoutTemplateUpdate.model_validate(data)


def test_workout_template_read_serializes_nested_orm_attributes() -> None:
    now = datetime.now(UTC)
    catalog_exercise_id = uuid4()
    template_set = SimpleNamespace(
        id=uuid4(),
        position=0,
        set_type="working",
        target_reps=8,
        target_weight_kg=Decimal("82.50"),
    )
    catalog_exercise = SimpleNamespace(
        id=catalog_exercise_id,
        code="bench_press",
        names={"en": "Bench press", "uk": "Жим лежачи"},
        muscle_groups=[
            SimpleNamespace(
                code="chest",
                names={"en": "Chest", "uk": "Груди"},
            )
        ],
        created_at=now,
        updated_at=now,
    )
    template_exercise = SimpleNamespace(
        id=uuid4(),
        exercise_id=catalog_exercise_id,
        position=0,
        notes="Controlled tempo",
        exercise=catalog_exercise,
        sets=[template_set],
    )
    template = SimpleNamespace(
        id=uuid4(),
        name="Push day",
        description=None,
        exercises=[template_exercise],
        created_at=now,
        updated_at=now,
    )

    result = WorkoutTemplateRead.model_validate(template)

    assert result.name == "Push day"
    assert result.exercises[0].exercise.names["uk"] == "Жим лежачи"
    assert result.exercises[0].sets[0].target_weight_kg == Decimal("82.50")

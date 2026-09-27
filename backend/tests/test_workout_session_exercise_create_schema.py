from uuid import uuid4

import pytest
from app.schemas.workout_session import WorkoutSessionExerciseCreate
from pydantic import ValidationError


def test_exercise_create_preserves_set_order_and_defaults() -> None:
    exercise_id = uuid4()
    result = WorkoutSessionExerciseCreate.model_validate(
        {"exercise_id": str(exercise_id), "sets": [{"set_type": "warmup"}, {}]}
    )
    assert result.exercise_id == exercise_id
    assert result.notes is None
    assert [item.set_type for item in result.sets] == ["warmup", "working"]


@pytest.mark.parametrize("notes", [None, "", "Повільний рух"])
def test_exercise_create_accepts_notes(notes: str | None) -> None:
    result = WorkoutSessionExerciseCreate.model_validate(
        {"exercise_id": str(uuid4()), "notes": notes, "sets": [{}]}
    )
    assert result.notes == notes


@pytest.mark.parametrize(
    "changes",
    [
        {"exercise_id": None},
        {"exercise_id": "invalid"},
        {"sets": []},
        {"sets": None},
        {"sets": [{"set_type": "invalid"}]},
        {"sets": [{"set_type": None}]},
        {"notes": 42},
        {"position": 1},
        {"user_id": str(uuid4())},
        {"sets": [{"planned_reps": 10}]},
        {"sets": [{"status": "completed"}]},
        {"sets": [{"actual_weight_kg": "20"}]},
    ],
)
def test_exercise_create_rejects_invalid_or_uneditable_fields(
    changes: dict[str, object],
) -> None:
    payload = {"exercise_id": str(uuid4()), "sets": [{}], **changes}
    with pytest.raises(ValidationError):
        WorkoutSessionExerciseCreate.model_validate(payload)


@pytest.mark.parametrize("field", ["exercise_id", "sets"])
def test_exercise_create_requires_catalog_id_and_sets(field: str) -> None:
    payload = {"exercise_id": str(uuid4()), "sets": [{}]}
    del payload[field]
    with pytest.raises(ValidationError) as error:
        WorkoutSessionExerciseCreate.model_validate(payload)
    assert error.value.errors()[0]["loc"] == (field,)

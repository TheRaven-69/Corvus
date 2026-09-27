from decimal import Decimal

import pytest
from app.schemas.workout_session import WorkoutSessionSetUpdate
from pydantic import ValidationError


@pytest.mark.parametrize(
    "payload",
    [
        {"actual_reps": 8},
        {"actual_reps": None},
        {"actual_weight_kg": None},
        {"actual_weight_kg": Decimal("0.00")},
        {"actual_weight_kg": Decimal("999999.99")},
        {"status": "pending"},
        {"status": "completed"},
        {"status": "skipped"},
        {"actual_reps": 8, "actual_weight_kg": Decimal("62.25"), "status": "completed"},
    ],
)
def test_set_update_preserves_only_explicit_fields(payload: dict[str, object]) -> None:
    request = WorkoutSessionSetUpdate.model_validate(payload)
    assert request.model_fields_set == set(payload)
    assert request.model_dump(exclude_unset=True) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {"actual_reps": 0},
        {"actual_reps": -1},
        {"actual_reps": 1.5},
        {"actual_weight_kg": "-0.01"},
        {"actual_weight_kg": "1000000.00"},
        {"actual_weight_kg": "1.001"},
        {"actual_weight_kg": "NaN"},
        {"actual_weight_kg": "Infinity"},
        {"status": None},
        {"status": "invalid"},
    ],
)
def test_set_update_rejects_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        WorkoutSessionSetUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "planned_reps",
        "planned_weight_kg",
        "completed_at",
        "user_id",
        "position",
        "set_type",
    ],
)
def test_set_update_rejects_uneditable_fields(field: str) -> None:
    with pytest.raises(ValidationError) as error:
        WorkoutSessionSetUpdate.model_validate({"actual_reps": 8, field: None})
    assert any(
        item["loc"] == (field,) and item["type"] == "extra_forbidden"
        for item in error.value.errors()
    )


def test_set_update_rejects_empty_request_with_clear_message() -> None:
    with pytest.raises(ValidationError, match="At least one field must be provided"):
        WorkoutSessionSetUpdate.model_validate({})

from uuid import uuid4

import pytest
from app.schemas.workout_session import WorkoutSessionExercisesReorder
from pydantic import ValidationError


@pytest.mark.parametrize("count", [1, 3])
def test_reorder_preserves_requested_order(count: int) -> None:
    ids = [uuid4() for _ in range(count)]
    result = WorkoutSessionExercisesReorder.model_validate(
        {"exercise_ids": [str(item) for item in ids]}
    )
    assert result.exercise_ids == ids


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"exercise_ids": []},
        {"exercise_ids": None},
        {"exercise_ids": "not-a-list"},
        {"exercise_ids": ["not-a-uuid"]},
        {"exercise_ids": [None]},
        {"exercise_ids": [str(uuid4())], "position": 0},
    ],
)
def test_reorder_rejects_invalid_input(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        WorkoutSessionExercisesReorder.model_validate(payload)


@pytest.mark.parametrize("mixed_representation", [False, True])
def test_reorder_rejects_duplicate_ids(mixed_representation: bool) -> None:
    exercise_id = uuid4()
    duplicate = str(exercise_id).upper() if mixed_representation else str(exercise_id)
    with pytest.raises(ValidationError, match="Exercise IDs must be unique"):
        WorkoutSessionExercisesReorder.model_validate(
            {"exercise_ids": [str(exercise_id), str(uuid4()), duplicate]}
        )

import pytest
from app.schemas.workout_session import (
    WorkoutSessionExerciseUpdate,
    WorkoutSessionUpdate,
)
from pydantic import BaseModel, ValidationError


@pytest.mark.parametrize("schema", [WorkoutSessionUpdate, WorkoutSessionExerciseUpdate])
@pytest.mark.parametrize("notes", ["Легке тренування", "", None])
def test_notes_update_accepts_text_and_explicit_clearing(
    schema: type[BaseModel], notes: str | None
) -> None:
    request = schema.model_validate({"notes": notes})
    assert request.model_dump() == {"notes": notes}


@pytest.mark.parametrize("schema", [WorkoutSessionUpdate, WorkoutSessionExerciseUpdate])
@pytest.mark.parametrize(
    "payload",
    [{}, {"notes": 42}, {"notes": []}, {"notes": "Text", "status": "completed"}],
)
def test_notes_update_rejects_missing_invalid_and_extra_fields(
    schema: type[BaseModel], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)

import pytest
from app.schemas.exercise import ExerciseCreate
from pydantic import ValidationError


def test_exercise_create_accepts_and_normalizes_valid_data() -> None:
    exercise = ExerciseCreate(
        name="  Жим гантелей  ",
        locale="uk",
        muscle_group_codes=["chest", "triceps"],
    )

    assert exercise.name == "Жим гантелей"
    assert exercise.locale == "uk"
    assert exercise.muscle_group_codes == ["chest", "triceps"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("locale", "de"),
        ("muscle_group_codes", []),
        ("muscle_group_codes", ["chest", "chest"]),
    ],
)
def test_exercise_create_rejects_invalid_data(
    field: str,
    value: object,
) -> None:
    data = {
        "name": "Жим гантелей",
        "locale": "uk",
        "muscle_group_codes": ["chest", "triceps"],
    }
    data[field] = value

    with pytest.raises(ValidationError):
        ExerciseCreate(**data)

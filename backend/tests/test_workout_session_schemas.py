from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.db.models import WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet
from app.schemas.workout_session import (
    WorkoutSessionCreate,
    WorkoutSessionExerciseRead,
    WorkoutSessionRead,
    WorkoutSessionSetRead,
)
from pydantic import ValidationError


@pytest.mark.parametrize("elapsed", [0, 1, 3600, 90061.9])
def test_session_read_calculates_complete_duration(elapsed: float) -> None:
    start = datetime(2026, 9, 18, 10, tzinfo=UTC)
    workout = WorkoutSession(
        id=uuid4(),
        name="History",
        status="completed",
        started_at=start,
        completed_at=start + timedelta(seconds=elapsed),
        exercises=[],
    )
    result = WorkoutSessionRead.model_validate(workout)
    assert result.duration_seconds == int(elapsed)
    assert result.model_dump(mode="json")["duration_seconds"] == int(elapsed)


@pytest.mark.parametrize("status", ["in_progress", "cancelled"])
def test_session_read_has_no_final_duration_before_completion(status: str) -> None:
    workout = WorkoutSession(
        id=uuid4(),
        name="Workout",
        status=status,
        started_at=datetime(2026, 9, 18, tzinfo=UTC),
        exercises=[],
    )
    result = WorkoutSessionRead.model_validate(workout).model_dump(mode="json")
    assert result["duration_seconds"] is None
    assert result["completed_at"] is None
    assert result["template_id"] is None


def test_session_read_duration_respects_timezone_offsets() -> None:
    workout = WorkoutSession(
        id=uuid4(),
        name="Workout",
        status="completed",
        started_at=datetime(2026, 9, 18, 10, tzinfo=UTC),
        completed_at=datetime(2026, 9, 18, 13, tzinfo=timezone(timedelta(hours=2))),
        exercises=[],
    )
    assert WorkoutSessionRead.model_validate(workout).duration_seconds == 3600


def test_session_read_serializes_full_nested_workout() -> None:
    start = datetime(2026, 9, 18, 10, tzinfo=UTC)
    workout = WorkoutSession(
        id=uuid4(),
        user_id=uuid4(),
        template_id=uuid4(),
        name="Strength",
        status="completed",
        notes="Good session",
        started_at=start,
        completed_at=start + timedelta(hours=1),
        exercises=[
            WorkoutSessionExercise(
                id=uuid4(),
                position=0,
                exercise_id=None,
                exercise_snapshot={
                    "names": {"uk": "Присідання"},
                    "muscle_groups": ["quadriceps"],
                },
                sets=[
                    WorkoutSessionSet(
                        id=uuid4(),
                        position=0,
                        set_type="working",
                        status="completed",
                        actual_reps=8,
                        completed_at=start + timedelta(minutes=10),
                    )
                ],
            )
        ],
    )
    result = WorkoutSessionRead.model_validate(workout).model_dump(mode="json")
    assert result["id"] == str(workout.id)
    assert result["template_id"] == str(workout.template_id)
    assert result["name"] == "Strength"
    assert result["notes"] == "Good session"
    assert result["started_at"] == "2026-09-18T10:00:00Z"
    assert result["completed_at"] == "2026-09-18T11:00:00Z"
    assert result["duration_seconds"] == 3600
    assert result["exercises"][0]["sets"][0]["actual_reps"] == 8
    assert "user_id" not in result


@pytest.mark.parametrize("catalog_id", [None, uuid4()])
def test_exercise_read_serializes_snapshot_and_nested_sets(
    catalog_id: UUID | None,
) -> None:
    snapshot = {
        "names": {"uk": "Присідання", "en": "Squat"},
        "muscle_groups": ["quadriceps", "glutes"],
    }
    exercise = WorkoutSessionExercise(
        id=uuid4(),
        session_id=uuid4(),
        exercise_id=catalog_id,
        position=0,
        exercise_snapshot=snapshot,
        notes="Controlled movement",
        sets=[
            WorkoutSessionSet(
                id=uuid4(),
                position=0,
                set_type="working",
                status="completed",
                planned_reps=10,
                actual_reps=8,
                actual_weight_kg=Decimal("60.00"),
                completed_at=datetime(2026, 9, 18, 10, tzinfo=UTC),
            )
        ],
    )
    result = WorkoutSessionExerciseRead.model_validate(exercise).model_dump(mode="json")
    assert result["id"] == str(exercise.id)
    assert result["exercise_id"] == (str(catalog_id) if catalog_id else None)
    assert result["exercise_snapshot"] == snapshot
    assert result["notes"] == "Controlled movement"
    assert result["sets"] == [
        WorkoutSessionSetRead.model_validate(exercise.sets[0]).model_dump(mode="json")
    ]
    assert "session_id" not in result


def test_exercise_read_allows_empty_sets_and_notes() -> None:
    exercise = WorkoutSessionExercise(
        id=uuid4(),
        position=0,
        exercise_id=None,
        exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
        sets=[],
    )
    result = WorkoutSessionExerciseRead.model_validate(exercise)
    assert result.notes is None
    assert result.sets == []


@pytest.mark.parametrize(
    "snapshot",
    [
        {"muscle_groups": []},
        {"names": {"en": "Squat"}},
        {"names": {"en": "Squat"}, "muscle_groups": "quadriceps"},
    ],
)
def test_exercise_read_rejects_malformed_snapshot(snapshot: dict[str, object]) -> None:
    exercise = WorkoutSessionExercise(
        id=uuid4(),
        position=0,
        exercise_snapshot=snapshot,
        sets=[],
    )
    with pytest.raises(ValidationError) as error:
        WorkoutSessionExerciseRead.model_validate(exercise)
    assert error.value.errors()[0]["loc"][0] == "exercise_snapshot"


@pytest.mark.parametrize("status", ["pending", "completed", "skipped"])
@pytest.mark.parametrize("set_type", ["warmup", "working"])
def test_set_read_serializes_orm_attributes(status: str, set_type: str) -> None:
    item_id = uuid4()
    completed_at = (
        datetime(2026, 9, 18, 10, tzinfo=UTC) if status == "completed" else None
    )
    item = WorkoutSessionSet(
        id=item_id,
        session_exercise_id=uuid4(),
        position=1,
        set_type=set_type,
        planned_reps=10,
        planned_weight_kg=Decimal("60.50"),
        actual_reps=8,
        actual_weight_kg=Decimal("62.25"),
        status=status,
        completed_at=completed_at,
    )
    result = WorkoutSessionSetRead.model_validate(item).model_dump(mode="json")
    assert result == {
        "id": str(item_id),
        "position": 1,
        "set_type": set_type,
        "planned_reps": 10,
        "planned_weight_kg": "60.50",
        "actual_reps": 8,
        "actual_weight_kg": "62.25",
        "status": status,
        "completed_at": "2026-09-18T10:00:00Z" if completed_at else None,
    }


def test_set_read_preserves_null_values() -> None:
    item = WorkoutSessionSet(
        id=uuid4(), position=0, set_type="working", status="pending"
    )
    result = WorkoutSessionSetRead.model_validate(item).model_dump(mode="json")
    for field in [
        "planned_reps",
        "planned_weight_kg",
        "actual_reps",
        "actual_weight_kg",
        "completed_at",
    ]:
        assert result[field] is None


@pytest.mark.parametrize("field", ["status", "set_type"])
def test_set_read_rejects_unknown_enum_values(field: str) -> None:
    item = WorkoutSessionSet(
        id=uuid4(), position=0, set_type="working", status="pending"
    )
    setattr(item, field, "unknown")
    with pytest.raises(ValidationError) as error:
        WorkoutSessionSetRead.model_validate(item)
    assert error.value.errors()[0]["loc"] == (field,)


def test_session_create_accepts_template_uuid_string() -> None:
    template_id = uuid4()
    request = WorkoutSessionCreate.model_validate({"template_id": str(template_id)})

    assert request.template_id == template_id
    assert request.model_dump(mode="json") == {"template_id": str(template_id)}


@pytest.mark.parametrize(
    "payload",
    [{}, {"template_id": None}, {"template_id": "bad-id"}, {"template_id": 42}],
)
def test_session_create_rejects_missing_or_invalid_template_id(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError) as error:
        WorkoutSessionCreate.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("template_id",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("user_id", str(uuid4())),
        ("status", "completed"),
        ("started_at", "2026-09-18T10:00:00Z"),
        ("completed_at", "2026-09-18T11:00:00Z"),
        ("name", "Client-supplied name"),
        ("exercises", []),
    ],
)
def test_session_create_rejects_extra_fields(field: str, value: object) -> None:
    with pytest.raises(ValidationError) as error:
        WorkoutSessionCreate.model_validate({"template_id": str(uuid4()), field: value})

    assert any(
        detail["loc"] == (field,) and detail["type"] == "extra_forbidden"
        for detail in error.value.errors()
    )

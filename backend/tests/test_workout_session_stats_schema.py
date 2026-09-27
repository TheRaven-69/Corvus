import pytest
from app.schemas.workout_session import WorkoutSessionStatsRead
from pydantic import ValidationError


@pytest.mark.parametrize("count,average", [(0, None), (1, 0.0), (2, 1800.5)])
def test_stats_serializes_count_and_average(count: int, average: float | None) -> None:
    result = WorkoutSessionStatsRead(
        completed_sessions_count=count, average_duration_seconds=average
    )
    assert result.model_dump(mode="json") == {
        "completed_sessions_count": count,
        "average_duration_seconds": average,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"completed_sessions_count": 0},
        {"average_duration_seconds": None},
        {"completed_sessions_count": -1, "average_duration_seconds": None},
        {"completed_sessions_count": 1, "average_duration_seconds": -0.1},
        {"completed_sessions_count": 1.5, "average_duration_seconds": 10},
    ],
)
def test_stats_rejects_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        WorkoutSessionStatsRead.model_validate(payload)

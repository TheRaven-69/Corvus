from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.db.models import WorkoutSession
from app.schemas.workout_session import WorkoutSessionHistoryRead
from pydantic import ValidationError


@pytest.mark.parametrize("limit", [1, 100])
def test_history_supports_empty_page_beyond_total(limit: int) -> None:
    result = WorkoutSessionHistoryRead(items=[], total=3, limit=limit, offset=10)
    assert result.model_dump() == {
        "items": [],
        "total": 3,
        "limit": limit,
        "offset": 10,
    }


def test_history_serializes_sessions_and_duration_in_order() -> None:
    start = datetime(2026, 9, 27, tzinfo=UTC)
    workouts = [
        WorkoutSession(
            id=uuid4(),
            name=status,
            status=status,
            started_at=start,
            completed_at=start + timedelta(minutes=45)
            if status == "completed"
            else None,
            exercises=[],
        )
        for status in ["completed", "cancelled"]
    ]
    page = WorkoutSessionHistoryRead(items=workouts, total=5, limit=2, offset=0)
    body = page.model_dump(mode="json")
    assert [item["id"] for item in body["items"]] == [str(w.id) for w in workouts]
    assert [item["duration_seconds"] for item in body["items"]] == [2700, None]
    assert body["total"] == 5


@pytest.mark.parametrize(
    "changes",
    [
        {"total": -1},
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"items": None},
        {"items": [{}]},
    ],
)
def test_history_rejects_invalid_page(changes: dict[str, object]) -> None:
    payload = {"items": [], "total": 0, "limit": 20, "offset": 0, **changes}
    with pytest.raises(ValidationError):
        WorkoutSessionHistoryRead.model_validate(payload)

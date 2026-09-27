from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.db.models import User, WorkoutSession
from app.repositories import workout_session as repository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def owners(db_session: AsyncSession):
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="Test",
            password_hash="test",
        )
        for name in ["stats_owner", "stats_other"]
    ]
    db_session.add_all(users)
    await db_session.commit()
    return [user.id for user in users]


@pytest.mark.parametrize(
    "durations,expected",
    [
        ([], None),
        ([0], 0.0),
        ([60], 60.0),
        ([60, 61], 60.5),
        ([3600, 7200, 10800], 7200.0),
        ([90000], 90000.0),
    ],
)
@pytest.mark.asyncio
async def test_stats_averages_only_owned_completed_sessions(
    db_session: AsyncSession, owners, durations: list[int], expected: float | None
) -> None:
    owner, other = owners
    start = datetime(2026, 9, 27, tzinfo=UTC)
    db_session.add_all(
        [
            WorkoutSession(
                user_id=owner,
                name="Completed",
                status="completed",
                started_at=start,
                completed_at=start + timedelta(seconds=seconds),
            )
            for seconds in durations
        ]
    )
    db_session.add_all(
        [
            WorkoutSession(
                user_id=owner, name="Active", status="in_progress", started_at=start
            ),
            WorkoutSession(
                user_id=owner, name="Cancelled", status="cancelled", started_at=start
            ),
            WorkoutSession(
                user_id=other,
                name="Private",
                status="completed",
                started_at=start,
                completed_at=start + timedelta(seconds=12345),
            ),
        ]
    )
    await db_session.commit()
    count, average = await repository.get_workout_session_stats(
        db_session, user_id=owner
    )
    assert count == len(durations)
    if expected is None:
        assert average is None
    else:
        assert isinstance(average, float)
        assert average == pytest.approx(expected)
    assert await repository.get_workout_session_stats(db_session, user_id=other) == (
        1,
        12345.0,
    )


@pytest.mark.asyncio
async def test_stats_for_user_without_sessions(
    db_session: AsyncSession, owners
) -> None:
    assert await repository.get_workout_session_stats(
        db_session, user_id=owners[0]
    ) == (0, None)

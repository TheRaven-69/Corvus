from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
)
from app.repositories import workout_session as repository
from app.schemas.workout_session import WorkoutSessionRead
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def history(db_session: AsyncSession):
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="Test",
            password_hash="test",
        )
        for name in ["history", "other"]
    ]
    db_session.add_all(users)
    await db_session.flush()
    start = datetime(2026, 9, 27, tzinfo=UTC)
    workouts = []
    for number, status, days in [
        (1, "completed", 0),
        (2, "cancelled", 1),
        (3, "completed", 1),
        (4, "in_progress", 2),
    ]:
        started = start + timedelta(days=days)
        workouts.append(
            WorkoutSession(
                id=UUID(int=number),
                user_id=users[0].id,
                name=str(number),
                status=status,
                started_at=started,
                completed_at=started + timedelta(hours=1)
                if status == "completed"
                else None,
                exercises=[
                    WorkoutSessionExercise(
                        position=p,
                        exercise_snapshot={
                            "names": {"en": str(p)},
                            "muscle_groups": [],
                        },
                        sets=[
                            WorkoutSessionSet(
                                position=s, set_type="working", planned_reps=8
                            )
                            for s in [1, 0]
                        ],
                    )
                    for p in [1, 0]
                ],
            )
        )
    workouts.append(
        WorkoutSession(
            user_id=users[1].id,
            name="Private",
            status="cancelled",
            started_at=start + timedelta(days=3),
        )
    )
    db_session.add_all(workouts)
    await db_session.commit()
    owner = users[0].id
    db_session.expunge_all()
    return owner


@pytest.mark.parametrize(
    "limit,offset,expected",
    [(2, 0, [3, 2]), (2, 2, [1]), (2, 3, []), (10, 20, []), (100, 0, [3, 2, 1])],
)
@pytest.mark.asyncio
async def test_history_paginates_owned_closed_sessions(
    db_session: AsyncSession, history, limit: int, offset: int, expected: list[int]
) -> None:
    items, total = await repository.get_workout_session_history(
        db_session, user_id=history, limit=limit, offset=offset
    )
    assert total == 3
    assert [item.id for item in items] == [UUID(int=i) for i in expected]
    assert all(
        item.user_id == history and item.status != "in_progress" for item in items
    )


@pytest.mark.asyncio
async def test_history_eager_loads_ordered_tree(
    db_session: AsyncSession, history
) -> None:
    items, _ = await repository.get_workout_session_history(
        db_session, user_id=history, limit=10, offset=0
    )
    db_session.expunge_all()
    for item in items:
        body = WorkoutSessionRead.model_validate(item)
        assert [e.position for e in body.exercises] == [0, 1]
        assert all([s.position for s in e.sets] == [0, 1] for e in body.exercises)
        assert body.duration_seconds == (3600 if item.status == "completed" else None)


@pytest.mark.asyncio
async def test_history_returns_empty_for_user_without_sessions(
    db_session: AsyncSession, history
) -> None:
    items, total = await repository.get_workout_session_history(
        db_session, user_id=uuid4(), limit=20, offset=0
    )
    assert items == [] and total == 0

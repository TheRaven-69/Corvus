from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import User, WorkoutSession
from app.schemas.workout_session import WorkoutSessionRead, WorkoutSessionUpdate
from app.services import workout_session as service
from app.services.exceptions import (
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.parametrize("notes", ["Легке тренування", "", None])
@pytest.mark.asyncio
async def test_update_session_notes_persists_without_changing_other_fields(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID], notes: str | None
) -> None:
    session_id, owner_id, _ = saved_session
    original = await db_session.get(WorkoutSession, session_id)
    assert original is not None
    original.notes = "Original notes"
    await db_session.commit()
    started_at = original.started_at
    result = await service.update_workout_session(
        db_session,
        user_id=owner_id,
        session_id=session_id,
        data=WorkoutSessionUpdate(notes=notes),
    )
    assert result.notes == notes
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSession, session_id)
    assert saved is not None
    assert saved.notes == notes
    assert saved.name == "Strength"
    assert saved.started_at == started_at
    assert saved.status == "in_progress"


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_update_session_notes_rejects_closed_session(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID], status: str
) -> None:
    session_id, owner_id, _ = saved_session
    workout = await db_session.get(WorkoutSession, session_id)
    assert workout is not None
    workout.status = status
    workout.completed_at = workout.started_at if status == "completed" else None
    workout.notes = "Keep"
    await db_session.commit()
    with pytest.raises(WorkoutSessionNotActiveError):
        await service.update_workout_session(
            db_session,
            user_id=owner_id,
            session_id=session_id,
            data=WorkoutSessionUpdate(notes="Change"),
        )
    await db_session.refresh(workout)
    assert workout.notes == "Keep"


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.asyncio
async def test_update_notes_rejects_other_owner_or_missing_session(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID], missing: bool
) -> None:
    session_id, owner_id, other_id = saved_session
    with pytest.raises(WorkoutSessionNotFoundError):
        await service.update_workout_session(
            db_session,
            user_id=owner_id if missing else other_id,
            session_id=uuid4() if missing else session_id,
            data=WorkoutSessionUpdate(notes="Forbidden"),
        )
    saved = await db_session.get(WorkoutSession, session_id)
    assert saved is not None and saved.notes is None


@pytest.mark.asyncio
async def test_update_notes_rolls_back_commit_failure(
    db_session: AsyncSession,
    saved_session: tuple[UUID, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_commit() -> None:
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    session_id, owner_id, _ = saved_session
    with pytest.raises(RuntimeError, match="Commit failed"):
        await service.update_workout_session(
            db_session,
            user_id=owner_id,
            session_id=session_id,
            data=WorkoutSessionUpdate(notes="Change"),
        )
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSession, session_id)
    assert saved is not None and saved.notes is None


@pytest_asyncio.fixture
async def saved_session(db_session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    users = [
        User(
            email=f"{name}@example.com",
            username=name,
            first_name=name,
            last_name="User",
            password_hash="not-a-real-hash",
        )
        for name in ["session_owner", "other_owner"]
    ]
    db_session.add_all(users)
    await db_session.flush()
    workout = WorkoutSession(user_id=users[0].id, name="Strength")
    db_session.add(workout)
    await db_session.commit()
    result = (workout.id, users[0].id, users[1].id)
    db_session.expunge_all()
    return result


@pytest.mark.asyncio
async def test_get_owned_session_returns_serializable_workout(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID]
) -> None:
    session_id, owner_id, _ = saved_session
    workout = await service.get_workout_session(
        db_session, user_id=owner_id, session_id=session_id
    )
    result = WorkoutSessionRead.model_validate(workout)
    assert result.id == session_id
    assert result.name == "Strength"


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.asyncio
async def test_get_session_raises_session_not_found_for_private_or_missing_resource(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID], missing: bool
) -> None:
    session_id, owner_id, other_id = saved_session
    with pytest.raises(WorkoutSessionNotFoundError, match="Workout session not found"):
        await service.get_workout_session(
            db_session,
            user_id=owner_id if missing else other_id,
            session_id=uuid4() if missing else session_id,
        )


@pytest.mark.asyncio
async def test_get_active_session_returns_owned_session_or_none(
    db_session: AsyncSession, saved_session: tuple[UUID, UUID, UUID]
) -> None:
    session_id, owner_id, other_id = saved_session
    workout = await service.get_active_workout_session(db_session, user_id=owner_id)
    assert workout is not None and workout.id == session_id
    assert (
        await service.get_active_workout_session(db_session, user_id=other_id) is None
    )

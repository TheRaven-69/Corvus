import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.db.models import (
    Exercise,
    ExerciseMuscleGroup,
    MuscleGroup,
    User,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutTemplate,
    WorkoutTemplateExercise,
)
from app.repositories.exercise import list_visible_exercises
from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def load_migration(filename: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEED = load_migration("54819c34e37a_seed_basic_system_exercises.py")
CATALOG = load_migration("aac1928a382a_create_exercise_catalog_tables.py")


async def run_seed(session: AsyncSession, direction: str) -> None:
    def execute(connection: Connection) -> None:
        with Operations.context(MigrationContext.configure(connection)):
            getattr(SEED, direction)()

    connection = await session.connection()
    await connection.run_sync(execute)


@pytest.fixture
def user() -> User:
    return User(
        email="seed@example.com",
        username="seed_owner",
        first_name="Seed",
        last_name="Owner",
        password_hash="not-a-real-hash",
    )


@pytest.mark.asyncio
async def test_seed_upgrade_and_downgrade_preserve_unrelated_data(
    db_session: AsyncSession, user: User
) -> None:
    await prepare_groups(db_session)
    custom = Exercise(owner=user, names={"uk": "Власна вправа"})
    unrelated = Exercise(code="unrelated", names={"en": "Other exercise"})
    db_session.add_all([custom, unrelated])
    await db_session.commit()
    unrelated_ids = {custom.id, unrelated.id}
    await run_seed(db_session, "upgrade")
    await db_session.commit()

    seeded = (
        await db_session.scalars(
            select(Exercise).where(Exercise.id.not_in(unrelated_ids))
        )
    ).all()
    assert len(seeded) == 16
    assert len({item.code for item in seeded}) == 16
    assert all(item.owner_user_id is None for item in seeded)
    assert all(set(item.names) == {"uk", "en"} for item in seeded)
    assert all(
        all(name.strip() == name and name for name in item.names.values())
        for item in seeded
    )
    assert all(
        item.created_at is not None and item.updated_at is not None for item in seeded
    )
    expected = {
        code: (uk, en, set(groups)) for code, uk, en, groups in SEED.BASIC_EXERCISES
    }
    for item in seeded:
        uk, en, groups = expected[item.code]
        assert item.names == {"uk": uk, "en": en}
        assert {group.code for group in item.muscle_groups} == groups
    seeded_ids = {item.id for item in seeded}
    assert seeded_ids <= {
        item.id for item in await list_visible_exercises(db_session, user.id)
    }
    assert seeded_ids <= {
        item.id for item in await list_visible_exercises(db_session, uuid4())
    }
    assert custom.id not in {
        item.id for item in await list_visible_exercises(db_session, uuid4())
    }

    await run_seed(db_session, "downgrade")
    await db_session.commit()
    assert set(await db_session.scalars(select(Exercise.id))) == unrelated_ids
    assert (
        await db_session.scalar(select(func.count()).select_from(ExerciseMuscleGroup))
        == 0
    )
    assert await db_session.scalar(select(func.count()).select_from(MuscleGroup)) == 10
    await run_seed(db_session, "upgrade")
    await db_session.commit()
    assert (
        set(await db_session.scalars(select(Exercise.id))) == unrelated_ids | seeded_ids
    )


async def prepare_groups(session: AsyncSession) -> None:
    # Capture the actual group seed from the existing catalog migration.
    class GroupCollector:
        def f(self, name: str) -> str:
            return name

        def create_table(self, *args, **kwargs) -> None:
            pass

        def create_index(self, *args, **kwargs) -> None:
            pass

        def bulk_insert(self, table, rows) -> None:
            session.add_all([MuscleGroup(**row) for row in rows])

    original = CATALOG.op
    try:
        CATALOG.op = GroupCollector()
        CATALOG.upgrade()
    finally:
        CATALOG.op = original
    await session.commit()


@pytest.mark.asyncio
async def test_seed_downgrade_rejects_template_references_without_partial_deletion(
    db_session: AsyncSession, user: User
) -> None:
    await prepare_groups(db_session)
    await run_seed(db_session, "upgrade")
    template = WorkoutTemplate(
        user=user,
        name="Keep template",
        exercises=[
            WorkoutTemplateExercise(
                exercise_id=SEED.exercise_id_for("crunch"), position=0
            )
        ],
    )
    db_session.add(template)
    await db_session.commit()
    link_count = await db_session.scalar(
        select(func.count()).select_from(ExerciseMuscleGroup)
    )
    with pytest.raises(IntegrityError):
        await run_seed(db_session, "downgrade")
    await db_session.rollback()
    assert await db_session.scalar(select(func.count()).select_from(Exercise)) == 16
    assert (
        await db_session.scalar(select(func.count()).select_from(ExerciseMuscleGroup))
        == link_count
    )
    assert (
        await db_session.scalar(
            select(func.count()).select_from(WorkoutTemplateExercise)
        )
        == 1
    )


@pytest.mark.asyncio
async def test_seed_downgrade_preserves_completed_session_snapshot(
    db_session: AsyncSession, user: User
) -> None:
    await prepare_groups(db_session)
    await run_seed(db_session, "upgrade")
    snapshot = {
        "names": {"en": "Crunch", "uk": "Скручування"},
        "muscle_groups": ["core"],
    }
    instant = datetime(2026, 9, 16, tzinfo=UTC)
    item = WorkoutSessionExercise(
        position=0,
        exercise_id=SEED.exercise_id_for("crunch"),
        exercise_snapshot=snapshot,
    )
    workout = WorkoutSession(
        user=user,
        name="History",
        status="completed",
        started_at=instant,
        completed_at=instant,
        exercises=[item],
    )
    db_session.add(workout)
    await db_session.commit()
    item_id = item.id
    await run_seed(db_session, "downgrade")
    await db_session.commit()
    db_session.expunge_all()
    saved = await db_session.get(WorkoutSessionExercise, item_id)
    assert saved is not None
    assert saved.exercise_id is None
    assert saved.exercise_snapshot == snapshot

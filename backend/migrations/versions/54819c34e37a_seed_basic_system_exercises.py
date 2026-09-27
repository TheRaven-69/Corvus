"""seed basic system exercises

Revision ID: 54819c34e37a
Revises: abf6a00427c1
Create Date: 2026-09-16 19:52:03.923839

"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54819c34e37a"
down_revision: str | Sequence[str] | None = "abf6a00427c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
EXERCISE_NAMESPACE = UUID("13ff7100-1b07-47e6-9952-84595657fbb3")
BASIC_EXERCISES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "barbell_bench_press",
        "Жим штанги лежачи",
        "Barbell bench press",
        ("chest", "triceps", "shoulders"),
    ),
    (
        "incline_dumbbell_bench_press",
        "Жим гантелей на похилій лаві",
        "Incline dumbbell bench press",
        ("chest", "triceps", "shoulders"),
    ),
    (
        "push_up",
        "Віджимання",
        "Push-up",
        ("chest", "triceps", "shoulders"),
    ),
    (
        "lat_pulldown",
        "Тяга верхнього блока",
        "Lat pulldown",
        ("back", "biceps"),
    ),
    (
        "seated_cable_row",
        "Горизонтальна тяга блока",
        "Seated cable row",
        ("back", "biceps"),
    ),
    (
        "one_arm_dumbbell_row",
        "Тяга гантелі однією рукою",
        "One-arm dumbbell row",
        ("back", "biceps"),
    ),
    (
        "seated_dumbbell_shoulder_press",
        "Жим гантелей сидячи",
        "Seated dumbbell shoulder press",
        ("shoulders", "triceps"),
    ),
    (
        "dumbbell_lateral_raise",
        "Підйом гантелей у сторони",
        "Dumbbell lateral raise",
        ("shoulders",),
    ),
    (
        "dumbbell_curl",
        "Згинання рук із гантелями",
        "Dumbbell curl",
        ("biceps",),
    ),
    (
        "cable_triceps_pushdown",
        "Розгинання рук на блоці",
        "Cable triceps pushdown",
        ("triceps",),
    ),
    (
        "barbell_squat",
        "Присідання зі штангою",
        "Barbell squat",
        ("quadriceps", "glutes"),
    ),
    (
        "leg_press",
        "Жим ногами",
        "Leg press",
        ("quadriceps", "glutes"),
    ),
    (
        "romanian_deadlift",
        "Румунська тяга",
        "Romanian deadlift",
        ("hamstrings", "glutes"),
    ),
    (
        "leg_curl",
        "Згинання ніг у тренажері",
        "Leg curl",
        ("hamstrings",),
    ),
    (
        "standing_calf_raise",
        "Підйом на носки стоячи",
        "Standing calf raise",
        ("calves",),
    ),
    (
        "crunch",
        "Скручування",
        "Crunch",
        ("core",),
    ),
)
exercises_table = sa.table(
    "exercises",
    sa.column("id", sa.Uuid()),
    sa.column("owner_user_id", sa.Uuid()),
    sa.column("code", sa.String(80)),
    sa.column("names", sa.JSON()),
)

exercise_muscle_groups_table = sa.table(
    "exercise_muscle_groups",
    sa.column("exercise_id", sa.Uuid()),
    sa.column("muscle_group_code", sa.String(40)),
)


def exercise_id_for(code: str) -> UUID:
    return uuid5(EXERCISE_NAMESPACE, code)


def upgrade() -> None:
    """Add the basic system exercise catalog."""
    exercise_rows: list[dict[str, object]] = []
    muscle_group_rows: list[dict[str, object]] = []

    for code, name_uk, name_en, muscle_group_codes in BASIC_EXERCISES:
        exercise_id = exercise_id_for(code)

        exercise_rows.append(
            {
                "id": exercise_id,
                "owner_user_id": None,
                "code": code,
                "names": {
                    "uk": name_uk,
                    "en": name_en,
                },
            }
        )

        for muscle_group_code in muscle_group_codes:
            muscle_group_rows.append(
                {
                    "exercise_id": exercise_id,
                    "muscle_group_code": muscle_group_code,
                }
            )

    op.bulk_insert(exercises_table, exercise_rows)
    op.bulk_insert(exercise_muscle_groups_table, muscle_group_rows)


def downgrade() -> None:
    """Remove only the system exercises introduced by this migration."""
    seeded_exercises = sa.or_(
        *(
            sa.and_(
                exercises_table.c.id == exercise_id_for(code),
                exercises_table.c.code == code,
            )
            for code, _, _, _ in BASIC_EXERCISES
        )
    )

    op.execute(
        sa.delete(exercises_table).where(
            exercises_table.c.owner_user_id.is_(None),
            seeded_exercises,
        )
    )

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status IN ('in_progress', 'cancelled') AND completed_at IS NULL)",
            name="completion_time_matches_status",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completion_not_before_start",
        ),
        Index(
            "uq_workout_sessions_user_in_progress",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
            sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workout_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="in_progress",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user: Mapped["User"] = relationship(
        back_populates="workout_sessions",
    )
    exercises: Mapped[list["WorkoutSessionExercise"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutSessionExercise.position",
    )


class WorkoutSessionExercise(Base):
    __tablename__ = "workout_session_exercises"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="position_non_negative",
        ),
        UniqueConstraint(
            "session_id",
            "position",
            name="uq_workout_session_exercises_session_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("exercises.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    exercise_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    session: Mapped["WorkoutSession"] = relationship(
        back_populates="exercises",
    )
    sets: Mapped[list["WorkoutSessionSet"]] = relationship(
        back_populates="session_exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutSessionSet.position",
    )


class WorkoutSessionSet(Base):
    __tablename__ = "workout_session_sets"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="position_non_negative",
        ),
        UniqueConstraint(
            "session_exercise_id",
            "position",
            name="uq_workout_session_sets_exercise_position",
        ),
        CheckConstraint(
            "set_type IN ('warmup', 'working')",
            name="set_type_allowed",
        ),
        CheckConstraint(
            "planned_reps IS NULL OR planned_reps > 0",
            name="planned_reps_positive",
        ),
        CheckConstraint(
            "actual_reps IS NULL OR actual_reps > 0",
            name="actual_reps_positive",
        ),
        CheckConstraint(
            "planned_weight_kg IS NULL OR planned_weight_kg >= 0",
            name="planned_weight_non_negative",
        ),
        CheckConstraint(
            "actual_weight_kg IS NULL OR actual_weight_kg >= 0",
            name="actual_weight_non_negative",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(status = 'completed' "
            "AND actual_reps IS NOT NULL "
            "AND completed_at IS NOT NULL) OR "
            "(status IN ('pending', 'skipped') "
            "AND completed_at IS NULL)",
            name="completion_fields_match_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    session_exercise_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_session_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    set_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    planned_reps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    planned_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    actual_reps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    actual_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    session_exercise: Mapped["WorkoutSessionExercise"] = relationship(
        back_populates="sets",
    )

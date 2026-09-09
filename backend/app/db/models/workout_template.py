from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exercise import Exercise
    from app.db.models.user import User


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

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
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user: Mapped["User"] = relationship(
        back_populates="workout_templates",
    )
    exercises: Mapped[list["WorkoutTemplateExercise"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutTemplateExercise.position",
    )


class WorkoutTemplateExercise(Base):
    __tablename__ = "workout_template_exercises"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="position_non_negative",
        ),
        UniqueConstraint(
            "template_id",
            "position",
            name="uq_workout_template_exercises_template_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    template_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    template: Mapped[WorkoutTemplate] = relationship(
        back_populates="exercises",
    )
    exercise: Mapped["Exercise"] = relationship(
        back_populates="workout_template_exercises",
    )
    sets: Mapped[list["WorkoutTemplateSet"]] = relationship(
        back_populates="template_exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutTemplateSet.position",
    )


class WorkoutTemplateSet(Base):
    __tablename__ = "workout_template_sets"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="position_non_negative",
        ),
        CheckConstraint(
            "set_type IN ('warmup', 'working')",
            name="set_type_allowed",
        ),
        CheckConstraint(
            "target_reps > 0",
            name="target_reps_positive",
        ),
        CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg >= 0",
            name="target_weight_non_negative",
        ),
        UniqueConstraint(
            "template_exercise_id",
            "position",
            name="uq_workout_template_sets_exercise_position",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    template_exercise_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_template_exercises.id", ondelete="CASCADE"),
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
    target_reps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    target_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    template_exercise: Mapped[WorkoutTemplateExercise] = relationship(
        back_populates="sets",
    )

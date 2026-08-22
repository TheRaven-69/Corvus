from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    code: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
    )
    names: Mapped[dict[str, str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    exercises: Mapped[list["Exercise"]] = relationship(
        secondary="exercise_muscle_groups",
        back_populates="muscle_groups",
    )


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NULL AND code IS NOT NULL) OR "
            "(owner_user_id IS NOT NULL AND code is NULL)",
            name="ownership_matches_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code: Mapped[str | None] = mapped_column(
        String(80),
        unique=True,
        nullable=True,
    )
    names: Mapped[dict[str, str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    muscle_groups: Mapped[list[MuscleGroup]] = relationship(
        secondary="exercise_muscle_groups",
        back_populates="exercises",
        lazy="selectin",
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
    owner: Mapped["User | None"] = relationship(
        back_populates="exercises",
    )


class ExerciseMuscleGroup(Base):
    __tablename__ = "exercise_muscle_groups"

    exercise_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        primary_key=True,
    )
    muscle_group_code: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("muscle_groups.code", ondelete="RESTRICT"),
        primary_key=True,
    )

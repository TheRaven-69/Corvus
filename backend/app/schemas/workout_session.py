from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class WorkoutSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: UUID


class WorkoutSessionSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    set_type: Literal["warmup", "working"]
    planned_reps: int | None
    planned_weight_kg: Decimal | None
    actual_reps: int | None
    actual_weight_kg: Decimal | None
    status: Literal["pending", "completed", "skipped"]
    completed_at: datetime | None


class WorkoutSessionExerciseSnapshotRead(BaseModel):
    names: dict[str, str]
    muscle_groups: list[str]


class WorkoutSessionExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID | None
    position: int
    exercise_snapshot: WorkoutSessionExerciseSnapshotRead
    notes: str | None
    sets: list[WorkoutSessionSetRead]


class WorkoutSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID | None
    name: str
    status: Literal["in_progress", "completed", "cancelled"]
    notes: str | None
    started_at: datetime
    completed_at: datetime | None
    exercises: list[WorkoutSessionExerciseRead]

    @computed_field
    @property
    def duration_seconds(self) -> int | None:
        if self.status != "completed" or self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at).total_seconds())


class WorkoutSessionSetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_reps: int | None = Field(default=None, gt=0)
    actual_weight_kg: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=8,
        decimal_places=2,
    )
    status: Literal["pending", "completed", "skipped"] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "WorkoutSessionSetUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Set status must not be null")

        return self


class WorkoutSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None


class WorkoutSessionExerciseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None


class WorkoutSessionSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    set_type: Literal["warmup", "working"] = "working"


class WorkoutSessionExerciseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_id: UUID
    notes: str | None = None
    sets: list[WorkoutSessionSetCreate] = Field(min_length=1)


class WorkoutSessionExercisesReorder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_exercises(self) -> "WorkoutSessionExercisesReorder":
        if len(self.exercise_ids) != len(set(self.exercise_ids)):
            raise ValueError("Exercise IDs must be unique")

        return self


class WorkoutSessionHistoryRead(BaseModel):
    items: list[WorkoutSessionRead]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class WorkoutSessionStatsRead(BaseModel):
    completed_sessions_count: int = Field(ge=0)
    average_duration_seconds: float | None = Field(ge=0)

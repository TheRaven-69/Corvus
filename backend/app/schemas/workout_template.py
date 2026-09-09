from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.exercise import ExerciseRead


class WorkoutTemplateSetCreate(BaseModel):
    position: int = Field(ge=0)
    set_type: Literal["warmup", "working"]
    target_reps: int = Field(gt=0)
    target_weight_kg: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=8,
        decimal_places=2,
    )


class WorkoutTemplateExerciseCreate(BaseModel):
    exercise_id: UUID
    position: int = Field(ge=0)
    notes: str | None = None
    sets: list[WorkoutTemplateSetCreate] = Field(min_length=1)

    @field_validator("sets")
    @classmethod
    def validate_unique_set_positions(
        cls,
        value: list[WorkoutTemplateSetCreate],
    ) -> list[WorkoutTemplateSetCreate]:
        positions = [workout_set.position for workout_set in value]

        if len(positions) != len(set(positions)):
            raise ValueError("Set positions must be unique")

        return value


class WorkoutTemplateCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )
    description: str | None = None
    exercises: list[WorkoutTemplateExerciseCreate] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_name = value.strip()

        if not normalized_name:
            raise ValueError("Workout template name must not be blank")

        return normalized_name

    @field_validator("exercises")
    @classmethod
    def validate_unique_exercise_positions(
        cls,
        value: list[WorkoutTemplateExerciseCreate],
    ) -> list[WorkoutTemplateExerciseCreate]:
        positions = [exercise.position for exercise in value]

        if len(positions) != len(set(positions)):
            raise ValueError("Exercise positions must be unique")

        return value


class WorkoutTemplateUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )
    description: str | None = None
    exercises: list[WorkoutTemplateExerciseCreate] | None = Field(
        default=None,
        min_length=1,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Workout template name must not be null")

        normalized_name = value.strip()

        if not normalized_name:
            raise ValueError("Workout template name must not be blank")

        return normalized_name

    @field_validator("exercises")
    @classmethod
    def validate_unique_exercise_positions(
        cls,
        value: list[WorkoutTemplateExerciseCreate] | None,
    ) -> list[WorkoutTemplateExerciseCreate]:
        if value is None:
            raise ValueError("Workout template exercises must not be null")

        positions = [exercise.position for exercise in value]

        if len(positions) != len(set(positions)):
            raise ValueError("Exercise positions must be unique")

        return value

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "WorkoutTemplateUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self


class WorkoutTemplateSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    set_type: Literal["warmup", "working"]
    target_reps: int
    target_weight_kg: Decimal | None


class WorkoutTemplateExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    position: int
    notes: str | None
    exercise: ExerciseRead
    sets: list[WorkoutTemplateSetRead]


class WorkoutTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    exercises: list[WorkoutTemplateExerciseRead]
    created_at: datetime
    updated_at: datetime

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExerciseCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )
    locale: Literal["en", "uk"]
    muscle_group_codes: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_name = value.strip()

        if not normalized_name:
            raise ValueError("Exercise name must not be blank")

        return normalized_name

    @field_validator("muscle_group_codes")
    @classmethod
    def validate_unique_muscle_groups(
        cls,
        value: list[str],
    ) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Muscle groups must be unique")

        return value


class MuscleGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    names: dict[str, str]


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str | None
    names: dict[str, str]
    muscle_groups: list[MuscleGroupRead]
    created_at: datetime
    updated_at: datetime

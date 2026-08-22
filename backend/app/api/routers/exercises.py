from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.db.models import Exercise, MuscleGroup
from app.schemas.exercise import ExerciseCreate, ExerciseRead, MuscleGroupRead
from app.services import exercise as exercise_service
from app.services.exceptions import UnknownMuscleGroupsError

router = APIRouter(tags=["exercises"])

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.get(
    "/muscle-groups",
    response_model=list[MuscleGroupRead],
)
async def get_muscle_groups(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[MuscleGroup]:
    return await exercise_service.list_muscle_groups(
        session,
    )


@router.get(
    "/exercises",
    response_model=list[ExerciseRead],
)
async def get_exercises(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[Exercise]:
    return await exercise_service.list_visible_exercises(
        session,
        current_user.id,
    )


@router.post(
    "/exercises",
    response_model=ExerciseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise(
    data: ExerciseCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> Exercise:
    try:
        return await exercise_service.create_custom_exercise(
            session,
            user_id=current_user.id,
            data=data,
        )
    except UnknownMuscleGroupsError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

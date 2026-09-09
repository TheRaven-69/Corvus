from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.db.models import WorkoutTemplate
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateRead,
    WorkoutTemplateUpdate,
)
from app.services import workout_template as workout_template_service
from app.services.exceptions import (
    UnavailableExercisesError,
    WorkoutTemplateNotFoundError,
)

router = APIRouter(
    prefix="/workout-templates",
    tags=["workout-templates"],
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.get(
    "",
    response_model=list[WorkoutTemplateRead],
)
async def get_workout_templates(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[WorkoutTemplate]:
    return await workout_template_service.list_workout_templates(
        session,
        user_id=current_user.id,
    )


@router.get(
    "/{template_id}",
    response_model=WorkoutTemplateRead,
)
async def get_workout_template(
    template_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutTemplate:
    try:
        return await workout_template_service.get_workout_template(
            session,
            user_id=current_user.id,
            template_id=template_id,
        )
    except WorkoutTemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.post(
    "",
    response_model=WorkoutTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout_template(
    data: WorkoutTemplateCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutTemplate:
    try:
        return await workout_template_service.create_workout_template(
            session,
            user_id=current_user.id,
            data=data,
        )
    except UnavailableExercisesError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.patch(
    "/{template_id}",
    response_model=WorkoutTemplateRead,
)
async def update_workout_template(
    template_id: UUID,
    data: WorkoutTemplateUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutTemplate:
    try:
        return await workout_template_service.update_workout_template(
            session,
            user_id=current_user.id,
            template_id=template_id,
            data=data,
        )
    except WorkoutTemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except UnavailableExercisesError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workout_template(
    template_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> Response:
    try:
        await workout_template_service.delete_workout_template(
            session,
            user_id=current_user.id,
            template_id=template_id,
        )
    except WorkoutTemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)

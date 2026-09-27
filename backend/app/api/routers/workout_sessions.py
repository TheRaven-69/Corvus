from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.db.models import WorkoutSession
from app.schemas.workout_session import (
    WorkoutSessionCreate,
    WorkoutSessionExerciseCreate,
    WorkoutSessionExercisesReorder,
    WorkoutSessionExerciseUpdate,
    WorkoutSessionHistoryRead,
    WorkoutSessionRead,
    WorkoutSessionSetCreate,
    WorkoutSessionSetUpdate,
    WorkoutSessionStatsRead,
    WorkoutSessionUpdate,
)
from app.services import workout_session as workout_session_service
from app.services.exceptions import (
    ActiveWorkoutSessionExistsError,
    InvalidWorkoutSessionExerciseOrderError,
    InvalidWorkoutSessionSetError,
    InvalidWorkoutTemplateError,
    UnavailableExercisesError,
    WorkoutSessionCancellationNotAllowedError,
    WorkoutSessionCompletionNotAllowedError,
    WorkoutSessionExerciseDeletionNotAllowedError,
    WorkoutSessionExerciseNotFoundError,
    WorkoutSessionExerciseReplacementNotAllowedError,
    WorkoutSessionNotActiveError,
    WorkoutSessionNotFoundError,
    WorkoutSessionSetDeletionNotAllowedError,
    WorkoutSessionSetNotFoundError,
    WorkoutTemplateNotFoundError,
)

router = APIRouter(
    prefix="/workout-sessions",
    tags=["workout-sessions"],
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.get(
    "/active",
    response_model=WorkoutSessionRead | None,
)
async def get_active_workout_session(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession | None:
    return await workout_session_service.get_active_workout_session(
        session,
        user_id=current_user.id,
    )


@router.get(
    "/stats",
    response_model=WorkoutSessionStatsRead,
)
async def get_workout_session_stats(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSessionStatsRead:
    return await workout_session_service.get_workout_session_stats(
        session,
        user_id=current_user.id,
    )


@router.get(
    "/{session_id}",
    response_model=WorkoutSessionRead,
)
async def get_workout_session(
    session_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.get_workout_session(
            session,
            user_id=current_user.id,
            session_id=session_id,
        )
    except WorkoutSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.post(
    "",
    response_model=WorkoutSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_workout_session(
    data: WorkoutSessionCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.start_workout_session(
            session,
            user_id=current_user.id,
            data=data,
        )
    except WorkoutTemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ActiveWorkoutSessionExistsError,
        InvalidWorkoutTemplateError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.patch(
    "/{session_id}/sets/{set_id}",
    response_model=WorkoutSessionRead,
)
async def update_workout_session_set(
    session_id: UUID,
    set_id: UUID,
    data: WorkoutSessionSetUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.update_workout_session_set(
            session,
            user_id=current_user.id,
            session_id=session_id,
            set_id=set_id,
            data=data,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionSetNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        WorkoutSessionNotActiveError,
        InvalidWorkoutSessionSetError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.patch(
    "/{session_id}",
    response_model=WorkoutSessionRead,
)
async def update_workout_session(
    session_id: UUID,
    data: WorkoutSessionUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.update_workout_session(
            session,
            user_id=current_user.id,
            session_id=session_id,
            data=data,
        )
    except WorkoutSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.patch(
    "/{session_id}/exercises/{exercise_id}",
    response_model=WorkoutSessionRead,
)
async def update_workout_session_exercise(
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionExerciseUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.update_workout_session_exercise(
            session,
            user_id=current_user.id,
            session_id=session_id,
            exercise_id=exercise_id,
            data=data,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionExerciseNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/exercises",
    response_model=WorkoutSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_workout_session_exercise(
    session_id: UUID,
    data: WorkoutSessionExerciseCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.add_workout_session_exercise(
            session,
            user_id=current_user.id,
            session_id=session_id,
            data=data,
        )
    except (
        WorkoutSessionNotFoundError,
        UnavailableExercisesError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/exercises/{exercise_id}/sets",
    response_model=WorkoutSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_workout_session_set(
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionSetCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.add_workout_session_set(
            session,
            user_id=current_user.id,
            session_id=session_id,
            exercise_id=exercise_id,
            data=data,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionExerciseNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.delete(
    "/{session_id}/sets/{set_id}",
    response_model=WorkoutSessionRead,
)
async def delete_workout_session_set(
    session_id: UUID,
    set_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.delete_workout_session_set(
            session,
            user_id=current_user.id,
            session_id=session_id,
            set_id=set_id,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionSetNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        WorkoutSessionNotActiveError,
        WorkoutSessionSetDeletionNotAllowedError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.delete(
    "/{session_id}/exercises/{exercise_id}",
    response_model=WorkoutSessionRead,
)
async def delete_workout_session_exercise(
    session_id: UUID,
    exercise_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.delete_workout_session_exercise(
            session,
            user_id=current_user.id,
            session_id=session_id,
            exercise_id=exercise_id,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionExerciseNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        WorkoutSessionNotActiveError,
        WorkoutSessionExerciseDeletionNotAllowedError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/exercises/{exercise_id}/replace",
    response_model=WorkoutSessionRead,
)
async def replace_workout_session_exercise(
    session_id: UUID,
    exercise_id: UUID,
    data: WorkoutSessionExerciseCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.replace_workout_session_exercise(
            session,
            user_id=current_user.id,
            session_id=session_id,
            exercise_id=exercise_id,
            data=data,
        )
    except (
        WorkoutSessionNotFoundError,
        WorkoutSessionExerciseNotFoundError,
        UnavailableExercisesError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        WorkoutSessionNotActiveError,
        WorkoutSessionExerciseReplacementNotAllowedError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/exercises/reorder",
    response_model=WorkoutSessionRead,
)
async def reorder_workout_session_exercises(
    session_id: UUID,
    data: WorkoutSessionExercisesReorder,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.reorder_workout_session_exercises(
            session,
            user_id=current_user.id,
            session_id=session_id,
            data=data,
        )
    except WorkoutSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        WorkoutSessionNotActiveError,
        InvalidWorkoutSessionExerciseOrderError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/complete",
    response_model=WorkoutSessionRead,
)
async def complete_workout_session(
    session_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.complete_workout_session(
            session,
            user_id=current_user.id,
            session_id=session_id,
        )
    except WorkoutSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionCompletionNotAllowedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/{session_id}/cancel",
    response_model=WorkoutSessionRead,
)
async def cancel_workout_session(
    session_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkoutSession:
    try:
        return await workout_session_service.cancel_workout_session(
            session,
            user_id=current_user.id,
            session_id=session_id,
        )
    except WorkoutSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except WorkoutSessionCancellationNotAllowedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=WorkoutSessionHistoryRead,
)
async def get_workout_session_history(
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkoutSessionHistoryRead:
    return await workout_session_service.get_workout_session_history(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.config import settings
from app.db.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRead, UserRegister
from app.services import auth as auth_service
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
    UsernameAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def set_refresh_cookie(
    response: Response,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/auth",
    )


def clear_refresh_cookie(
    response: Response,
) -> None:
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        secure=not settings.debug,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegister,
    session: DatabaseSession,
) -> User:
    try:
        return await auth_service.register_user(
            session,
            data,
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from error
    except UsernameAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        ) from error
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from error


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    response: Response,
    session: DatabaseSession,
) -> TokenResponse:
    try:
        result = await auth_service.login_user(
            session,
            data,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from error

    set_refresh_cookie(
        response,
        result.refresh_token,
    )

    return TokenResponse(access_token=result.access_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[
        str | None,
        Cookie(),
    ] = None,
) -> TokenResponse:
    try:
        result = await auth_service.refresh_tokens(
            session,
            refresh_token,
        )
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from error

    set_refresh_cookie(
        response,
        result.refresh_token,
    )

    return TokenResponse(
        access_token=result.access_token,
    )


@router.get(
    "/me",
    response_model=UserRead,
)
async def get_me(
    current_user: CurrentUser,
) -> User:
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[
        str | None,
        Cookie(),
    ] = None,
) -> None:
    await auth_service.logout_user(
        session,
        refresh_token,
    )

    clear_refresh_cookie(response)

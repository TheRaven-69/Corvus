from app.services.exceptions.auth import (
    AuthServiceError,
    EmailAlreadyExistsError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from app.services.exceptions.exercise import (
    ExerciseServiceError,
    UnknownMuscleGroupsError,
)
from app.services.exceptions.workout_template import (
    UnavailableExercisesError,
    WorkoutTemplateNotFoundError,
    WorkoutTemplateServiceError,
)

__all__ = [
    "AuthServiceError",
    "EmailAlreadyExistsError",
    "ExerciseServiceError",
    "InvalidAccessTokenError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "UnavailableExercisesError",
    "UnknownMuscleGroupsError",
    "UserAlreadyExistsError",
    "UsernameAlreadyExistsError",
    "WorkoutTemplateNotFoundError",
    "WorkoutTemplateServiceError",
]

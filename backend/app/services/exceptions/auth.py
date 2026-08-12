class AuthServiceError(Exception):
    """Base exception for authentication use cases."""


class UserAlreadyExistsError(AuthServiceError):
    """User conflicts with an existing account."""


class EmailAlreadyExistsError(UserAlreadyExistsError):
    """Email is already registered."""


class UsernameAlreadyExistsError(UserAlreadyExistsError):
    """Username is already registered."""


class InvalidCredentialsError(AuthServiceError):
    """Login or password is incorrect."""


class InvalidRefreshTokenError(AuthServiceError):
    """Refresh token is missing, expired, revoked, or unknown."""


class InvalidAccessTokenError(AuthServiceError):
    """Access token is invalid, expired, or belongs to an inactive session."""

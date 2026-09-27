class WorkoutSessionServiceError(Exception):
    pass


class WorkoutSessionNotFoundError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Workout session not found")


class ActiveWorkoutSessionExistsError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("An active workout session already exists")


class InvalidWorkoutTemplateError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__(
            "A workout template must contain exercises "
            "and each exercise must contain at least one set"
        )


class WorkoutSessionNotActiveError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Only an active workout session can be modified")


class WorkoutSessionSetNotFoundError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Workout session set not found")


class InvalidWorkoutSessionSetError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("A completed set must have actual repetitions")


class WorkoutSessionExerciseNotFoundError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Workout session exercise not found")


class WorkoutSessionSetDeletionNotAllowedError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Cannot delete a completed set or the last set of an exercise")


class WorkoutSessionExerciseDeletionNotAllowedError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Cannot delete an exercise with completed sets")


class WorkoutSessionExerciseReplacementNotAllowedError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("Cannot replace an exercise with completed sets")


class InvalidWorkoutSessionExerciseOrderError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Exercise IDs must include every session exercise exactly once"
        )


class WorkoutSessionCompletionNotAllowedError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Only an active session with at least one completed set can be completed"
        )


class WorkoutSessionCancellationNotAllowedError(WorkoutSessionServiceError):
    def __init__(self) -> None:
        super().__init__("A completed session cannot be cancelled")

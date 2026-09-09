from uuid import UUID


class WorkoutTemplateServiceError(Exception):
    pass


class WorkoutTemplateNotFoundError(WorkoutTemplateServiceError):
    def __init__(self) -> None:
        super().__init__("Workout template not found")


class UnavailableExercisesError(WorkoutTemplateServiceError):
    def __init__(self, exercise_ids: set[UUID]) -> None:
        self.exercise_ids = exercise_ids

        sorted_ids = sorted(exercise_ids, key=str)
        message = "Unavailable exercises: " + ", ".join(
            str(exercise_id) for exercise_id in sorted_ids
        )
        super().__init__(message)

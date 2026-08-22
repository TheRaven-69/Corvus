class ExerciseServiceError(Exception):
    pass


class UnknownMuscleGroupsError(ExerciseServiceError):
    def __init__(self, codes: list[str]) -> None:
        self.codes = codes

        message = "Unknown muscle groups: " + ", ".join(codes)
        super().__init__(message)

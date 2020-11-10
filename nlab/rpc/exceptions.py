
class ApiError(ValueError):
    def __init__(self, *, code, message):
        super().__init__(message)
        self.code = code

    @property
    def errors(self):
        return {
            "message": str(self),
            "code": self.code,
        }

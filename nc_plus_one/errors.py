"""Business failures translated to HTTP responses by the application entry point."""


class ApplicationError(Exception):
    code: str


class NotFoundError(ApplicationError):
    code = "NOT_FOUND"


class ConflictError(ApplicationError):
    code = "CONFLICT"


class UnauthorizedError(ApplicationError):
    code = "UNAUTHORIZED"

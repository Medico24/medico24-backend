"""Custom application exceptions."""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500):
        """Initialize exception with message and status code."""
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found"):
        """Initialize with 404 status code."""
        super().__init__(message, status_code=404)


class UnauthorizedException(AppException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Unauthorized"):
        """Initialize with 401 status code."""
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden"):
        """Initialize with 403 status code."""
        super().__init__(message, status_code=403)


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Bad request"):
        """Initialize with 400 status code."""
        super().__init__(message, status_code=400)


class ConflictException(AppException):
    """Conflict exception."""

    def __init__(self, message: str = "Conflict"):
        """Initialize with 409 status code."""
        super().__init__(message, status_code=409)


class ValidationException(AppException):
    """Validation error exception."""

    def __init__(self, message: str = "Validation error"):
        """Initialize with 422 status code."""
        super().__init__(message, status_code=422)


class RateLimitException(AppException):
    """Rate limit exceeded exception."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """Initialize with 429 status code."""
        super().__init__(message, status_code=429)

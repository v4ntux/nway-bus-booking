from typing import Any


class DomainError(Exception):
    """Business-rule failure mapped to a unified HTTP error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=404)


class ConflictError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=409)


class ForbiddenError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=403)


class UnauthorizedError(DomainError):
    def __init__(self, code: str = "UNAUTHORIZED", message: str = "Authentication required") -> None:
        super().__init__(code, message, status_code=401)

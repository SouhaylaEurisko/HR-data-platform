"""
Domain-level errors for the HR platform.

HTTP status codes are assigned only in ``exception_handlers`` (or explicitly
in rare router-only cases), not in services.
"""


class AppError(Exception):
    """Base for application errors surfaced to clients."""

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self._default_message()
        super().__init__(self.message)

    def _default_message(self) -> str:
        return "Request could not be completed."


# --- 401 Authentication ---


class AuthenticationError(AppError):
    """Invalid or missing authentication."""


class CredentialsRequiredError(AuthenticationError):
    """No bearer token was provided."""

    def _default_message(self) -> str:
        return "Could not validate credentials"


class TokenExpiredError(AuthenticationError):
    """JWT is past expiry."""

    def _default_message(self) -> str:
        return "Token has expired. Please login again."


class InvalidTokenError(AuthenticationError):
    """Token missing subject, bad signature, or malformed."""

    def _default_message(self) -> str:
        return "Could not validate credentials"


class InvalidCredentialsError(AuthenticationError):
    """Wrong email/password at login."""

    def _default_message(self) -> str:
        return "Invalid email or password."


# --- 403 Authorization ---


class AuthorizationError(AppError):
    """Authenticated but not allowed to perform the action."""


class AccountDeactivatedError(AuthorizationError):
    """User exists but is_active is false."""

    def _default_message(self) -> str:
        return "Your account has been deactivated. Contact an HR manager."


class InsufficientPermissionsError(AuthorizationError):
    """Role does not allow the operation (e.g. not HR manager)."""

    def _default_message(self) -> str:
        return "Only HR managers can perform this action."


# --- 404 / 409 / 400 ---


class NotFoundError(AppError):
    """Resource does not exist or is not visible."""

    def _default_message(self) -> str:
        return "Resource not found."


class ConflictError(AppError):
    """Request conflicts with current state (e.g. duplicate email)."""

    def _default_message(self) -> str:
        return "Request conflicts with existing data."


class BusinessRuleError(AppError):
    """Client error: validation or business rule failed (HTTP 400)."""

    def _default_message(self) -> str:
        return "Invalid request."


# --- 500 ---


class InternalError(AppError):
    """Unexpected failure after validation (HTTP 500)."""

    def _default_message(self) -> str:
        return "An unexpected error occurred."

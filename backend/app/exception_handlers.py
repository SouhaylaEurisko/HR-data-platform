"""
Register FastAPI exception handlers — map domain errors to HTTP responses.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    AccountDeactivatedError,
    AppError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    CredentialsRequiredError,
    InternalError,
    InvalidCredentialsError,
    InvalidTokenError,
    InsufficientPermissionsError,
    NotFoundError,
    TokenExpiredError,
)

_BEARER = {"WWW-Authenticate": "Bearer"}


def _json(detail: str, status_code: int, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers or {},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if isinstance(exc, TokenExpiredError):
        return _json(exc.message, status.HTTP_401_UNAUTHORIZED, _BEARER)
    if isinstance(exc, InvalidTokenError):
        return _json(exc.message, status.HTTP_401_UNAUTHORIZED, _BEARER)
    if isinstance(exc, CredentialsRequiredError):
        return _json(exc.message, status.HTTP_401_UNAUTHORIZED, _BEARER)
    if isinstance(exc, InvalidCredentialsError):
        return _json(exc.message, status.HTTP_401_UNAUTHORIZED, _BEARER)
    if isinstance(exc, AuthenticationError):
        return _json(exc.message, status.HTTP_401_UNAUTHORIZED, _BEARER)

    if isinstance(exc, InsufficientPermissionsError):
        return _json(exc.message, status.HTTP_403_FORBIDDEN)
    if isinstance(exc, AccountDeactivatedError):
        return _json(exc.message, status.HTTP_403_FORBIDDEN)
    if isinstance(exc, AuthorizationError):
        return _json(exc.message, status.HTTP_403_FORBIDDEN)

    if isinstance(exc, NotFoundError):
        return _json(exc.message, status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ConflictError):
        return _json(exc.message, status.HTTP_409_CONFLICT)
    if isinstance(exc, BusinessRuleError):
        return _json(exc.message, status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, InternalError):
        return _json(exc.message, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return _json(exc.message, status.HTTP_500_INTERNAL_SERVER_ERROR)


async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    return _json(str(exc) or "Resource not found.", status.HTTP_404_NOT_FOUND)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(FileNotFoundError, file_not_found_handler)

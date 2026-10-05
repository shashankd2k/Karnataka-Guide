"""
Typed domain exceptions and global API error handlers.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger("app.errors")

# Starlette / FastAPI status compatibility
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(
        self,
        message: str = "Invalid request parameters or payload.",
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        message: str = "Requested resource was not found.",
        code: str = "NOT_FOUND",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


# Alias for NotFoundError
NotFoundException = NotFoundError


class ValidationException(AppException):
    """Data validation exception."""

    def __init__(
        self,
        message: str = "Data validation error occurred.",
        code: str = "VALIDATION_ERROR",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=HTTP_422,
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required exception."""

    def __init__(
        self,
        message: str = "Authentication is required to access this resource.",
        code: str = "UNAUTHORIZED",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenException(AppException):
    """Access forbidden exception."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictException(AppException):
    """Conflict error exception."""

    def __init__(
        self,
        message: str = "Resource conflict occurred.",
        code: str = "CONFLICT",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ServiceUnavailableException(AppException):
    """Subsystem unavailable exception."""

    def __init__(
        self,
        message: str = "Requested service is temporarily unavailable.",
        code: str = "SERVICE_UNAVAILABLE",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def build_error_envelope(
    code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details,
        }
    }


def get_request_id(request: Request) -> Optional[str]:
    """Extract request ID from request state or header."""
    return getattr(request.state, "request_id", request.headers.get("X-Request-ID"))


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    req_id = get_request_id(request)
    logger.warning(
        "app_exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=req_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=exc.code,
            message=exc.message,
            request_id=req_id,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI/Pydantic request validation errors."""
    req_id = get_request_id(request)
    errors = exc.errors()
    simplified_details = [
        {
            "loc": err.get("loc", []),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in errors
    ]
    logger.warning(
        "validation_error",
        error_count=len(errors),
        request_id=req_id,
    )
    return JSONResponse(
        status_code=HTTP_422,
        content=build_error_envelope(
            code="VALIDATION_ERROR",
            message="Request body or query parameters failed validation.",
            request_id=req_id,
            details=simplified_details,
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle generic Starlette HTTP exceptions (e.g. 404 for route not found)."""
    req_id = get_request_id(request)
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=code,
            message=str(exc.detail),
            request_id=req_id,
            details=None,
        ),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    req_id = get_request_id(request)
    logger.error(
        "unhandled_exception",
        error=str(exc),
        exc_info=True,
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_envelope(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            request_id=req_id,
            details=None,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all global error handlers onto the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

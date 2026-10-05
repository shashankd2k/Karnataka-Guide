"""
ASGI middleware for request correlation and context tracking.
"""

import re
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.errors import build_error_envelope

SAFE_REQ_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
logger = structlog.get_logger("app.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns and propagates a unique X-Request-ID header."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        
        if incoming_id and SAFE_REQ_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex

        # Attach to request state for handlers and errors
        request.state.request_id = request_id

        # Bind to structlog contextvars for automatic correlation in all log entries
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_middleware_exception",
                error=str(exc),
                exc_info=True,
                request_id=request_id,
            )
            response = JSONResponse(
                status_code=500,
                content=build_error_envelope(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected internal server error occurred.",
                    request_id=request_id,
                    details=None,
                ),
            )
        finally:
            structlog.contextvars.clear_contextvars()

        # Ensure response header carries the correlation ID
        response.headers["X-Request-ID"] = request_id
        return response

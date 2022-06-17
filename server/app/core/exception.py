import json
import logging
from collections import defaultdict
from typing import Any

from asgi_correlation_id.context import correlation_id
from fastapi.exceptions import RequestValidationError as ValidationError
from httpx import HTTPStatusError, RequestError
from starlette.requests import Request
from starlette.responses import JSONResponse

VALIDATION_ERROR_MESSAGE = "Invalid request; see details."

logger = logging.getLogger(__name__)


def _exception_response(
    request: Request,
    message: str,
    details: Any = None,
    status_code: int = 500,
    source: str = "pmc api",
) -> JSONResponse:
    """Create a JSON error response."""
    content = {
        "message": message,
        "url": str(request.url),
        "source": source,
    }
    if details:
        content["details"] = details
    return JSONResponse(content=content, status_code=status_code)


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    errors = defaultdict(list)
    for error in exc.errors():
        errors[error["loc"][1]].append(error["msg"])

    return _exception_response(
        request,
        VALIDATION_ERROR_MESSAGE,
        details=errors,
        status_code=422,  # fastapi uses 422 for validation errors
    )


async def pulp_exception_handler(request: Request, exc: HTTPStatusError) -> JSONResponse:
    """Pulp exception handler."""
    logger.exception(exc)

    if exc.response.status_code == 400:
        return _exception_response(
            request,
            VALIDATION_ERROR_MESSAGE,
            details=json.loads(exc.response.content.decode()),
            source="pulp",
            status_code=400,
        )
    elif exc.response.status_code == 404:
        return _exception_response(
            request,
            "Requested resource not found.",
            source="pulp",
            status_code=404,
        )
    else:
        return _exception_response(
            request,
            f"Received {exc.response.status_code} response from Pulp.",
            source="pulp",
            status_code=502,
        )


async def httpx_exception_handler(request: Request, exc: RequestError) -> JSONResponse:
    """httpx exception handler."""
    logger.exception(exc)

    return _exception_response(request, f"{type(exc).__name__} while requesting {exc.request.url}.")


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Generic exception handler for all other exceptions."""
    logger.exception(exc)

    response = _exception_response(
        request, f"Unexpected exception {type(exc).__name__}.", details=str(exc)
    )

    # for generic exceptions, middleware is bypassed so manually add correlation id headers
    response.headers.append("X-Correlation-ID", correlation_id.get() or "")
    response.headers.append("Access-Control-Expose-Headers", "X-Correlation-ID")

    return response

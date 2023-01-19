import json
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Union

from fastapi.exceptions import RequestValidationError as ValidationError
from httpx import HTTPStatusError, RequestError
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette.responses import JSONResponse

VALIDATION_ERROR_MESSAGE = "Invalid request; see details."

logger = logging.getLogger(__name__)


def _exception_response(
    request: Request,
    message: str,
    detail: Any = None,
    status_code: int = 500,
    source: str = "pmc api",
) -> JSONResponse:
    """Create a JSON error response."""
    content = {
        "message": message,
        "url": str(request.url),
        "source": source,
    }
    if detail:
        content["detail"] = detail
    return JSONResponse(content=content, status_code=status_code)


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    errors = defaultdict(list)
    for error in exc.errors():
        errors[error["loc"][-1]].append(error["msg"])

    return _exception_response(
        request,
        VALIDATION_ERROR_MESSAGE,
        detail=errors,
        status_code=422,  # fastapi uses 422 for validation errors
    )


async def pulp_exception_handler(request: Request, exc: HTTPStatusError) -> JSONResponse:
    """Pulp exception handler."""
    logger.exception(exc)

    if exc.response.status_code == 400:
        return _exception_response(
            request,
            VALIDATION_ERROR_MESSAGE,
            detail=json.loads(exc.response.content.decode()),
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


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """IntegrityError handler."""
    logger.exception(exc)

    uniq_const = r'duplicate key value violates unique constraint "\w+"\nDETAIL:  Key \((.*)\)='
    if match := re.search(uniq_const, exc.orig.args[0]):
        field = match.group(1)

        # format message/detail be consistent with Pulp
        message = VALIDATION_ERROR_MESSAGE
        detail: Union[Dict[str, List[str]], str] = {field: ["This field must be unique."]}
    else:
        # fall back to just showing the exception message
        message = f"Unexpected exception {type(exc).__name__}."
        detail = str(exc)

    return _exception_response(request, message, detail=detail, status_code=409)


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Generic exception handler for all other exceptions."""
    logger.exception(exc)

    return _exception_response(
        request, f"Unexpected exception {type(exc).__name__}.", detail=str(exc)
    )

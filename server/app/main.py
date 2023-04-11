import logging
import logging.config
import time
from typing import Any, Awaitable, Callable, Dict

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError as ValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from httpx import HTTPStatusError, RequestError
from sqlalchemy.exc import IntegrityError
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware

from app.api.routes.api import router as api_router
from app.core.config import settings
from app.core.exception import (
    exception_handler,
    httpx_exception_handler,
    integrity_error_handler,
    pulp_exception_handler,
    validation_exception_handler,
)
from app.core.log_config import DEFAULT_LOG_CONFIG

# setup loggers
if settings.LOGGING_CONFIG:
    LOG_CONFIG = settings.LOGGING_CONFIG
    logging.config.fileConfig(settings.LOGGING_CONFIG, disable_existing_loggers=False)
else:
    LOG_CONFIG = DEFAULT_LOG_CONFIG
    logging.config.dictConfig(DEFAULT_LOG_CONFIG)

logger = logging.getLogger(__name__)

root_router = APIRouter()
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# This is essentially the same thing that starlette does for you if you add an exception handler,
# except that it behaves differently by default if you add one for Exception.
# Add it early so that it runs before other middleware.
# See discussion in https://msazure.visualstudio.com/One/_workitems/edit/16819067
app.add_middleware(ExceptionMiddleware, handlers={Exception: exception_handler})


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start_time = time.time()

    if request.url.path != "/healthz/":
        message = f"request from {request.client.host}:{request.client.port}"  # type: ignore
        message += f" cli:{request.headers.get('pmc-cli-version')}"
        message += f" - {request.method} {request.url.path}"
        logger.info(message)

    response = await call_next(request)

    if request.url.path != "/healthz/":
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)
        logger.info(
            f"request completed_in={formatted_process_time}ms status_code={response.status_code}."
        )

    return response


@app.middleware("http")
async def close_httpx_client(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    finally:
        if client := context.get("httpx_client", None):
            # If this request called out to pulp then this was created by PulpApi.request
            logger.debug("Closing Pulp httpx client")
            await client.aclose()


@root_router.get("/", response_class=RedirectResponse, status_code=302)
def root() -> str:
    logger.info("root request")
    return "/api/"


@root_router.get("/api/", status_code=200)
def api(request: Request) -> Dict[str, Any]:
    return {
        "server": {"version": settings.VERSION},
        "versions": {"v4": "v4/"},
    }


@root_router.get("/healthz/")
def healthz(request: Request) -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(root_router)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
app.add_middleware(RawContextMiddleware)

app.add_exception_handler(HTTPStatusError, pulp_exception_handler)
app.add_exception_handler(RequestError, httpx_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)

if __name__ == "__main__":
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_config=LOG_CONFIG,
    )

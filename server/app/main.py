import logging
import logging.config
import random
import string
import time
from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError as ValidationError
from fastapi.requests import Request
from fastapi.responses import RedirectResponse, Response
from httpx import HTTPStatusError, RequestError

from api.routes.api import router as api_router
from core.config import settings
from core.exception import (
    exception_handler,
    httpx_exception_handler,
    pulp_exception_handler,
    validation_exception_handler,
)

# setup loggers
logging.config.fileConfig(settings.LOGGING_CONFIG, disable_existing_loggers=False)

logger = logging.getLogger(__name__)

root_router = APIRouter()
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)
    logger.info(
        f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
    )

    return response


@root_router.get("/", response_class=RedirectResponse, status_code=302)
def root() -> str:
    logger.info("root request")
    return "/api"


@root_router.get("/api/", status_code=200)
def api() -> Dict[str, Any]:
    logger.info("Received request for /api/")
    return {
        "server": {"version": settings.VERSION},
        "versions": {"v4": "v4/"},
    }


app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(root_router)

app.add_exception_handler(HTTPStatusError, pulp_exception_handler)
app.add_exception_handler(RequestError, httpx_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, exception_handler)

if __name__ == "__main__":
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level=("debug" if settings.DEBUG else "info"),
        log_config=settings.LOGGING_CONFIG,
    )

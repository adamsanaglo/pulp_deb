from typing import Any, Dict

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from api.routes.api import router as api_router
from core.config import settings

root_router = APIRouter()
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)


@root_router.get("/", response_class=RedirectResponse, status_code=302)
def root() -> str:
    return "/api"


@root_router.get("/api", status_code=200)
def api() -> Dict[str, Any]:
    return {
        "server": {"version": settings.VERSION},
        "versions": {"v4": "v4/"},
    }


app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(root_router)


if __name__ == "__main__":
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level=("debug" if settings.DEBUG else "info"),
    )

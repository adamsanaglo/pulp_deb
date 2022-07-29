import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requires_repo_admin
from app.core.schemas import DebRepoId, Pagination, ReleaseCreate, ReleaseListResponse, TaskResponse
from app.services.pulp.api import ReleaseApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/{repo_id}/releases/", response_model=ReleaseListResponse)
async def list_releases(repo_id: DebRepoId, pagination: Pagination = Depends(Pagination)) -> Any:
    async with ReleaseApi() as api:
        return await api.list(pagination, {"repository": repo_id})


@router.post(
    "/repositories/{repo_id}/releases/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_repo_admin)],
)
async def create_release(repo_id: DebRepoId, release: ReleaseCreate) -> Any:
    params = release.dict()
    params["repository"] = repo_id
    async with ReleaseApi() as api:
        # check first if the release already exists
        search = {k: v for k, v in params.items() if k not in ["components", "architectures"]}
        releases = await api.list(params=search)
        if len(releases["results"]) > 0:
            raise HTTPException(status_code=409, detail="Release already exists.")

        return await api.create(params)

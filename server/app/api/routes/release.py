import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requires_repo_admin
from app.core.schemas import (
    DebRepoId,
    PackageId,
    Pagination,
    ReleaseCreate,
    ReleaseListResponse,
    TaskResponse,
)
from app.services.pulp.api import ReleaseApi, RepositoryApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/repositories/{repo_id}/releases/",
    response_model=ReleaseListResponse,
    response_model_exclude_unset=True,
)
async def list_releases(
    repo_id: DebRepoId,
    pagination: Pagination = Depends(Pagination),
    name: Optional[str] = None,
    package: Optional[PackageId] = None,
) -> Any:
    async with ReleaseApi() as api:
        params: Dict[str, Any] = {"repository": repo_id}
        if name:
            params["distribution"] = name
        if package:
            params["package"] = package.uuid
        return await api.list(pagination, params)


@router.post(
    "/repositories/{repo_id}/releases/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_repo_admin)],
)
async def create_release(repo_id: DebRepoId, release: ReleaseCreate) -> Any:
    params = release.dict()
    params["repository"] = repo_id

    # populate origin and label
    async with RepositoryApi() as api:
        repo = await api.read(repo_id)
        repo_name = repo["name"]
    if repo_name.endswith("-apt"):
        repo_name = repo_name[:-4]
    params["origin"] = params["label"] = f"{repo_name} {release.distribution}"

    async with ReleaseApi() as api:
        # check first if the release already exists
        search = {k: v for k, v in params.items() if k not in ["components", "architectures"]}
        releases = await api.list(params=search)
        if len(releases["results"]) > 0:
            raise HTTPException(status_code=409, detail="Release already exists.")

        return await api.create(params)

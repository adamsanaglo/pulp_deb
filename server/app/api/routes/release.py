import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requires_repo_admin
from app.core.schemas import (
    DebRepoId,
    PackageId,
    Pagination,
    ReleaseCreate,
    ReleaseId,
    ReleaseListResponse,
    TaskResponse,
)
from app.services.pulp.api import ReleaseApi, RepositoryApi
from app.services.pulp.content_manager import ContentManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/repositories/{repo_id}/releases/",
    response_model_exclude_unset=True,
    response_model=ReleaseListResponse,
)
async def list_releases(
    repo_id: DebRepoId,
    pagination: Pagination = Depends(Pagination),
    name: Optional[str] = None,
    package: Optional[PackageId] = None,
) -> Any:
    params: Dict[str, Any] = {"repository": repo_id}
    if name:
        params["distribution"] = name
    if package:
        params["package"] = package.uuid
    return await ReleaseApi.list(pagination, params)


@router.post(
    "/repositories/{repo_id}/releases/",
    dependencies=[Depends(requires_repo_admin)],
    response_model=TaskResponse,
)
async def create_release(repo_id: DebRepoId, release: ReleaseCreate) -> Any:
    params = release.dict()
    params["repository"] = repo_id

    # populate origin and label
    repo = await RepositoryApi.read(repo_id)
    repo_name = repo["name"]
    if repo_name.endswith("-apt"):
        repo_name = repo_name[:-4]
    params["origin"] = params["label"] = f"{repo_name} {release.distribution}"

    # check first if the release already exists
    search = {k: v for k, v in params.items() if k not in ["components", "architectures"]}
    releases = await ReleaseApi.list(params=search)
    if len(releases["results"]) > 0:
        raise HTTPException(status_code=409, detail="Release already exists.")

    return await ReleaseApi.create(params)


@router.delete(
    "/repositories/{repo}/releases/{release}/",
    dependencies=[Depends(requires_repo_admin)],
    response_model=TaskResponse,
)
async def delete_release(repo: DebRepoId, release: ReleaseId) -> Any:
    cm = ContentManager(id=repo)
    return await cm.remove_release(release)

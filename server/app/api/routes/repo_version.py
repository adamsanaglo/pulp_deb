import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends

from app.core.schemas import PackageId, Pagination, RepoVersionId
from app.services.pulp.api import RepoVersionApi

router = APIRouter()
logger = logging.getLogger(__name__)

# TODO: define the response model for repo version


@router.get("/repository_versions/")
async def list(
    pagination: Pagination = Depends(Pagination),
    repository: Optional[str] = None,
    number: Optional[int] = None,
    package: Optional[PackageId] = None,
) -> Any:
    params = dict(repository=repository, number=number, content=package)

    return await RepoVersionApi.list(
        pagination,
        params=params,
    )


@router.get("/repository_versions/{id}/")
async def read(id: RepoVersionId) -> Any:
    return await RepoVersionApi.read(id)


@router.delete("/repository_versions/{id}/")
async def delete(id: RepoVersionId) -> Any:
    return await RepoVersionApi.destroy(id)

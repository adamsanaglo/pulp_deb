from typing import Any, Optional

from fastapi import APIRouter, Depends

from app.api.auth import requires_repo_admin
from app.core.schemas import (
    DistributionCreate,
    DistributionListResponse,
    DistributionResponse,
    DistributionUpdate,
    DistroId,
    Pagination,
    RepoId,
    TaskResponse,
)
from app.services.pulp.api import DistributionApi

router = APIRouter()


@router.get("/distributions/", response_model=DistributionListResponse)
async def list_distros(
    pagination: Pagination = Depends(Pagination),
    repository: Optional[RepoId] = None,
    name: Optional[str] = None,
    name__contains: Optional[str] = None,
    base_path: Optional[str] = None,
    base_path__contains: Optional[str] = None,
    ordering: Optional[str] = None,
) -> Any:
    return await DistributionApi.list(
        pagination,
        params={
            "repository": repository,
            "name": name,
            "name__contains": name__contains,
            "base_path": base_path,
            "base_path__contains": base_path__contains,
            "ordering": ordering,
        },
    )


@router.post(
    "/distributions/", dependencies=[Depends(requires_repo_admin)], response_model=TaskResponse
)
async def create_distribution(distro: DistributionCreate) -> Any:
    return await DistributionApi.create(distro.dict(exclude_unset=True))


@router.get("/distributions/{id}/", response_model=DistributionResponse)
async def read_distribution(id: DistroId) -> Any:
    return await DistributionApi.read(id)


@router.patch(
    "/distributions/{id}/", dependencies=[Depends(requires_repo_admin)], response_model=TaskResponse
)
async def update_distribution(id: DistroId, distro: DistributionUpdate) -> Any:
    data = distro.dict(exclude_unset=True)
    return await DistributionApi.update(id, data)


@router.delete(
    "/distributions/{id}/", dependencies=[Depends(requires_repo_admin)], response_model=TaskResponse
)
async def delete_distribution(id: DistroId) -> Any:
    return await DistributionApi.destroy(id)

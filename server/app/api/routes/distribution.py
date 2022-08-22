from typing import Any

from fastapi import APIRouter, Depends

from app.api.auth import requires_repo_admin
from app.core.schemas import (
    DistributionCreate,
    DistributionListResponse,
    DistributionResponse,
    DistributionUpdate,
    DistroId,
    Pagination,
    TaskResponse,
)
from app.services.pulp.api import DistributionApi

router = APIRouter()


@router.get("/distributions/", response_model=DistributionListResponse)
async def list_distros(pagination: Pagination = Depends(Pagination)) -> Any:
    async with DistributionApi() as api:
        return await api.list(pagination)


@router.post(
    "/distributions/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def create_distribution(distro: DistributionCreate) -> Any:
    async with DistributionApi() as api:
        return await api.create(distro.dict(exclude_unset=True))


@router.get("/distributions/{id}/", response_model=DistributionResponse)
async def read_distribution(id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.read(id)


@router.patch(
    "/distributions/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def update_distribution(id: DistroId, distro: DistributionUpdate) -> Any:
    data = distro.dict(exclude_unset=True)

    async with DistributionApi() as api:
        return await api.update(id, data)


@router.delete(
    "/distributions/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def delete_distribution(id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.destroy(id)
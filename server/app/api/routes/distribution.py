from typing import Optional

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


@router.get("/distributions/")
async def list_distros(
    pagination: Pagination = Depends(Pagination),
    name: Optional[str] = None,
    name__contains: Optional[str] = None,
    base_path: Optional[str] = None,
    base_path__contains: Optional[str] = None,
) -> DistributionListResponse:
    return await DistributionApi.list(
        pagination,
        params={
            "name": name,
            "name__contains": name__contains,
            "base_path": base_path,
            "base_path__contains": base_path__contains,
        },
    )


@router.post("/distributions/", dependencies=[Depends(requires_repo_admin)])
async def create_distribution(distro: DistributionCreate) -> TaskResponse:
    return await DistributionApi.create(distro.dict(exclude_unset=True))


@router.get("/distributions/{id}/")
async def read_distribution(id: DistroId) -> DistributionResponse:
    return await DistributionApi.read(id)


@router.patch("/distributions/{id}/", dependencies=[Depends(requires_repo_admin)])
async def update_distribution(id: DistroId, distro: DistributionUpdate) -> TaskResponse:
    data = distro.dict(exclude_unset=True)
    return await DistributionApi.update(id, data)


@router.delete("/distributions/{id}/", dependencies=[Depends(requires_repo_admin)])
async def delete_distribution(id: DistroId) -> TaskResponse:
    return await DistributionApi.destroy(id)

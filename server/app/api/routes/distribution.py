from typing import Any

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi_microsoft_identity import requires_auth

from core.schemas import Distribution, DistributionUpdate, DistroId, Pagination
from services.pulp.api import DistributionApi

router = APIRouter()


@router.get("/distributions/")
@requires_auth
async def list_distros(request: Request, pagination: Pagination = Depends(Pagination)) -> Any:
    async with DistributionApi() as api:
        return await api.list(pagination)


@router.post("/distributions/")
@requires_auth
async def create_distribution(request: Request, distro: Distribution) -> Any:
    async with DistributionApi() as api:
        return await api.create(distro.dict(exclude_unset=True))


@router.get("/distributions/{id}/")
@requires_auth
async def read_distribution(request: Request, id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.read(id)


@router.patch("/distributions/{id}/")
@requires_auth
async def update_distribution(request: Request, id: DistroId, distro: DistributionUpdate) -> Any:
    data = distro.dict(exclude_unset=True)

    async with DistributionApi() as api:
        return await api.update(id, data)


@router.delete("/distributions/{id}/")
@requires_auth
async def delete_distribution(request: Request, id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.destroy(id)

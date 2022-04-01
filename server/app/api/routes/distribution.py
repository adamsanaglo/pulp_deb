from typing import Any

from fastapi import APIRouter

from core.schemas import Distribution, DistributionUpdate, DistroId
from services.pulp.api import DistributionApi

router = APIRouter()


@router.get("/distributions/")
async def list_distros() -> Any:
    async with DistributionApi() as api:
        return await api.list()


@router.post("/distributions/")
async def create_distribution(distro: Distribution) -> Any:
    async with DistributionApi() as api:
        return await api.create(distro.dict(exclude_unset=True))


@router.get("/distributions/{id}/")
async def read_distribution(id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.read(id)


@router.patch("/distributions/{id}/")
async def update_distribution(id: DistroId, distro: DistributionUpdate) -> Any:
    data = distro.dict(exclude_unset=True)

    async with DistributionApi() as api:
        return await api.update(id, data)


@router.delete("/distributions/{id}/")
async def delete_distribution(id: DistroId) -> Any:
    async with DistributionApi() as api:
        return await api.destroy(id)

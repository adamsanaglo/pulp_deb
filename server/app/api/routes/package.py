from typing import Any, Optional

from core.schemas import PackageId, PackageType, Pagination
from fastapi import APIRouter, Depends, UploadFile
from services.package.verify import verify_signature
from services.pulp.api import PackageApi

router = APIRouter()


@router.get("/deb/packages/")
async def deb_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.deb)


@router.get("/rpm/packages/")
async def rpm_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.rpm)


@router.post("/packages/")
async def create_package(
    file: UploadFile, force_name: Optional[bool] = False, ignore_signature: Optional[bool] = False
) -> Any:
    if not ignore_signature:
        await verify_signature(file)
    async with PackageApi() as api:
        return await api.create({"file": file, "force_name": force_name})


@router.get("/packages/{id}/")
async def read_package(id: PackageId) -> Any:
    async with PackageApi() as api:
        return await api.read(id)

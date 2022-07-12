from typing import Any, Optional

from fastapi import APIRouter, Depends, UploadFile

from core.schemas import (
    DebPackageListResponse,
    PackageId,
    PackageResponse,
    PackageType,
    Pagination,
    RpmPackageListResponse,
    TaskResponse,
)
from services.package.verify import verify_signature
from services.pulp.api import PackageApi

router = APIRouter()


@router.get("/deb/packages/", response_model=DebPackageListResponse)
async def deb_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.deb)


@router.get("/rpm/packages/", response_model=RpmPackageListResponse)
async def rpm_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.rpm)


@router.post("/packages/", response_model=TaskResponse)
async def create_package(
    file: UploadFile, force_name: Optional[bool] = False, ignore_signature: Optional[bool] = False
) -> Any:
    if not ignore_signature:
        await verify_signature(file)
    async with PackageApi() as api:
        return await api.create({"file": file, "force_name": force_name})


@router.get("/packages/{id}/", response_model=PackageResponse)
async def read_package(id: PackageId) -> Any:
    async with PackageApi() as api:
        return await api.read(id)

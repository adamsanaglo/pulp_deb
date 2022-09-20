from typing import Any, Optional

from fastapi import APIRouter, Depends, UploadFile

from app.api.auth import requires_package_admin_or_publisher
from app.core.schemas import (
    DebPackageListResponse,
    PackageId,
    PackageResponse,
    PackageType,
    Pagination,
    RpmPackageListResponse,
    TaskResponse,
)
from app.services.package.verify import verify_signature
from app.services.pulp.api import PackageApi

router = APIRouter()


@router.get("/deb/packages/", response_model=DebPackageListResponse)
async def deb_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.deb)


@router.get("/rpm/packages/", response_model=RpmPackageListResponse)
async def rpm_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.rpm)


@router.post(
    "/packages/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_package_admin_or_publisher)],
)
async def create_package(file: UploadFile, ignore_signature: Optional[bool] = False) -> Any:
    if not ignore_signature:
        await verify_signature(file)
    async with PackageApi() as api:
        return await api.create({"file": file})


@router.get("/packages/{id}/", response_model=PackageResponse)
async def read_package(id: PackageId) -> Any:
    async with PackageApi() as api:
        return await api.read(id)

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.auth import requires_package_admin_or_publisher
from app.core.schemas import (
    DebPackageListResponse,
    DebPackageQuery,
    FilePackageListResponse,
    PackageId,
    PackageType,
    Pagination,
    PythonPackageListResponse,
    RpmPackageListResponse,
    RpmPackageQuery,
    TaskResponse,
)
from app.services.package.verify import verify_signature
from app.services.pulp.api import PackageApi

router = APIRouter()


@router.get("/deb/packages/", response_model=DebPackageListResponse)
async def deb_packages(
    pagination: Pagination = Depends(Pagination), query: DebPackageQuery = Depends()
) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, params=query.dict(), type=PackageType.deb)


@router.get("/rpm/packages/", response_model=RpmPackageListResponse)
async def rpm_packages(
    pagination: Pagination = Depends(Pagination), query: RpmPackageQuery = Depends()
) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, params=query.dict(), type=PackageType.rpm)


@router.get("/python/packages/", response_model=PythonPackageListResponse)
async def python_packages(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.python)


@router.get("/file/packages/", response_model=FilePackageListResponse)
async def files(pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.list(pagination, type=PackageType.file)


@router.post(
    "/packages/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_package_admin_or_publisher)],
)
async def create_package(
    file: UploadFile,
    ignore_signature: Optional[bool] = False,
    file_type: Optional[PackageType] = None,
) -> Any:
    if not file_type:
        # attempt to resolve the file type using ext
        extension = Path(file.filename).suffix.lstrip(".")
        if extension == "whl":
            file_type = PackageType.python
        elif extension == "deb":
            file_type = PackageType.deb
        elif extension == "rpm":
            file_type = PackageType.rpm
        else:
            raise HTTPException(
                status_code=422, detail=f"Unrecognized file extension: {extension}."
            )

    if not ignore_signature and file_type in [PackageType.deb, PackageType.rpm]:
        await verify_signature(file)
    async with PackageApi() as api:
        return await api.create({"file": file, "file_type": file_type})


@router.get("/packages/{id}/")
async def read_package(id: PackageId) -> Any:
    async with PackageApi() as api:
        return await api.read(id)

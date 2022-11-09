from pathlib import Path
from typing import Any, Optional, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import AnyHttpUrl

from app.api.auth import requires_package_admin_or_publisher
from app.core.schemas import (
    DebPackageListResponse,
    DebPackageQuery,
    DebPackageResponse,
    FilePackageListResponse,
    FilePackageResponse,
    FullDebPackageResponse,
    FullFilePackageResponse,
    FullPythonPackageResponse,
    FullRpmPackageResponse,
    PackageId,
    PackageType,
    Pagination,
    PythonPackageListResponse,
    PythonPackageResponse,
    RpmPackageListResponse,
    RpmPackageQuery,
    RpmPackageResponse,
    TaskResponse,
)
from app.services.package.verify import UnsignedPackage, verify_signature
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
    file: Optional[UploadFile] = None,
    url: Optional[AnyHttpUrl] = None,
    ignore_signature: Optional[bool] = False,
    file_type: Optional[PackageType] = None,
    relative_path: Optional[str] = None,
) -> Any:
    if not file and not url:
        raise HTTPException(status_code=422, detail="Must upload a file or specify url.")

    if url:
        resp = httpx.get(url)
        file = UploadFile(Path(resp.url.path).name)
        await file.write(resp.content)
        await file.seek(0)
    assert file is not None

    if not file_type:
        # attempt to resolve the file type using ext
        types = {".whl": PackageType.python, ".deb": PackageType.deb, ".rpm": PackageType.rpm}
        extension = Path(file.filename).suffix
        if not (file_type := types.get(extension, None)):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Could not determine package type from '{extension}' "
                    "extension. Please specify the file type."
                ),
            )

    data = {"file": file, "file_type": file_type}

    if relative_path:
        if file_type != PackageType.file:
            raise HTTPException(
                status_code=422, detail=f"Cannot set relative path for {file_type} packages."
            )
        else:
            data["relative_path"] = relative_path

    if not ignore_signature and file_type in [PackageType.deb, PackageType.rpm]:
        try:
            await verify_signature(file)
        except UnsignedPackage as exc:
            raise HTTPException(status_code=422, detail=f"{exc.__class__.__name__}: {exc}")
    async with PackageApi() as api:
        return await api.create(data)


@router.get(
    "/packages/{id}/",
    response_model=Union[
        FullDebPackageResponse,
        FullRpmPackageResponse,
        FullPythonPackageResponse,
        DebPackageResponse,
        RpmPackageResponse,
        PythonPackageResponse,
        FullFilePackageResponse,
        FilePackageResponse,
    ],
)
async def read_package(id: PackageId, details: bool = False) -> Any:
    resp_model = ("Full" if details else "") + id.type.title() + "PackageResponse"
    async with PackageApi() as api:
        data = await api.read(id)
        return globals()[resp_model](**data)

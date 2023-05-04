from pathlib import Path
from typing import Any, Optional, Type, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import AnyHttpUrl

from app.api.auth import requires_package_admin_or_publisher
from app.api.routes.artifact import create_artifact
from app.core.schemas import (
    BasePackageResponse,
    DebPackageListResponse,
    DebPackageQuery,
    DebPackageResponse,
    DebSourcePackageListResponse,
    DebSourcePackageQuery,
    DebSourcePackageResponse,
    FilePackageListResponse,
    FilePackageQuery,
    FilePackageResponse,
    FullDebPackageResponse,
    FullDebSourcePackageResponse,
    FullFilePackageResponse,
    FullPythonPackageResponse,
    FullRpmPackageResponse,
    PackageId,
    PackageType,
    Pagination,
    PythonPackageListResponse,
    PythonPackageQuery,
    PythonPackageResponse,
    RpmPackageListResponse,
    RpmPackageQuery,
    RpmPackageResponse,
    TaskResponse,
)
from app.services.package.verify import PackageSignatureError, verify_signature
from app.services.pulp.api import PackageApi

router = APIRouter()


def _field_list(response: Type[BasePackageResponse]) -> str:
    # use pulp's fields parameter to request specific fields and limit response size
    fields = list(response.schema(by_alias=False)["properties"].keys())
    fields.append("pulp_href")
    return (",").join(fields)


@router.get("/deb/packages/", response_model=DebPackageListResponse)
async def deb_packages(
    pagination: Pagination = Depends(Pagination), query: DebPackageQuery = Depends()
) -> Any:
    params = query.dict(exclude_none=True)
    params["fields"] = _field_list(DebPackageResponse)
    return await PackageApi.list(pagination, params=params, type=PackageType.deb)


@router.get("/deb_src/packages/", response_model=DebSourcePackageListResponse)
async def deb_src_packages(
    pagination: Pagination = Depends(Pagination), query: DebSourcePackageQuery = Depends()
) -> Any:
    params = query.dict(exclude_none=True)
    return await PackageApi.list(pagination, params=params, type=PackageType.deb_src)


@router.get("/rpm/packages/", response_model=RpmPackageListResponse)
async def rpm_packages(
    pagination: Pagination = Depends(Pagination), query: RpmPackageQuery = Depends()
) -> Any:
    params = query.dict(exclude_none=True)
    params["fields"] = _field_list(RpmPackageResponse)
    return await PackageApi.list(pagination, params=params, type=PackageType.rpm)


@router.get("/python/packages/", response_model=PythonPackageListResponse)
async def python_packages(
    pagination: Pagination = Depends(Pagination), query: PythonPackageQuery = Depends()
) -> Any:
    params = query.dict(exclude_none=True)
    params["fields"] = _field_list(PythonPackageResponse)
    return await PackageApi.list(pagination, params=params, type=PackageType.python)


@router.get("/file/packages/", response_model=FilePackageListResponse)
async def files(
    pagination: Pagination = Depends(Pagination), query: FilePackageQuery = Depends()
) -> Any:
    params = query.dict(exclude_none=True)
    params["fields"] = _field_list(FilePackageResponse)
    return await PackageApi.list(pagination, params=params, type=PackageType.file)


@router.post(
    "/packages/",
    dependencies=[Depends(requires_package_admin_or_publisher)],
    response_model=TaskResponse,
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
        types = {
            ".whl": PackageType.python,
            ".deb": PackageType.deb,
            ".rpm": PackageType.rpm,
            ".dsc": PackageType.deb_src,
        }
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
            await verify_signature(file, file_type)
        except PackageSignatureError as exc:
            raise HTTPException(status_code=422, detail=f"{exc.__class__.__name__}: {exc}")

    if file_type == PackageType.deb_src:
        # create the dsc file artifact, if it doesn't exist.
        artifact = await create_artifact(file)
        data["artifact"] = artifact["id"]

    return await PackageApi.create(data)


@router.get(
    "/packages/{id}/",
    response_model=Union[
        FullDebPackageResponse,
        FullRpmPackageResponse,
        FullPythonPackageResponse,
        DebSourcePackageResponse,
        FullDebSourcePackageResponse,
        DebPackageResponse,
        RpmPackageResponse,
        PythonPackageResponse,
        FullFilePackageResponse,
        FilePackageResponse,
    ],
)
async def read_package(id: PackageId, details: bool = False) -> Any:
    resp_model = ("Full" if details else "") + id.type.resp_model
    data = await PackageApi.read(id)
    return globals()[resp_model](**data)

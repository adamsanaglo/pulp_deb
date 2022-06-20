from typing import Any, Optional

from fastapi import APIRouter, UploadFile

from core.schemas import PackageId
from services.pulp.api import PackageApi

router = APIRouter()


@router.get("/packages/")
async def list_packages() -> Any:
    async with PackageApi() as api:
        return await api.list()


@router.post("/packages/")
async def create_package(file: UploadFile, force_name: Optional[bool] = False) -> Any:
    async with PackageApi() as api:
        return await api.create({"file": file, "force_name": force_name})


@router.get("/packages/{id}/")
async def read_package(id: PackageId) -> Any:
    async with PackageApi() as api:
        return await api.read(id)

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.auth import requires_repo_admin
from app.core.schemas import (
    Pagination,
    RemoteCreate,
    RemoteId,
    RemoteListResponse,
    RemoteResponse,
    RemoteUpdate,
    TaskResponse,
)
from app.services.pulp.api import RemoteApi

router = APIRouter()


@router.get("/remotes/")
async def list_remotes(
    pagination: Pagination = Depends(Pagination), name: Optional[str] = None
) -> RemoteListResponse:
    return await RemoteApi.list(pagination, params={"name": name})


@router.post("/remotes/", dependencies=[Depends(requires_repo_admin)])
async def create_remote(remote: RemoteCreate) -> RemoteResponse:
    return await RemoteApi.create(remote.dict(exclude_unset=True))


@router.get("/remotes/{id}/")
async def read_remote(id: RemoteId) -> RemoteResponse:
    return await RemoteApi.read(id)


@router.patch("/remotes/{id}/", dependencies=[Depends(requires_repo_admin)])
async def update_remote(id: RemoteId, remote: RemoteUpdate) -> TaskResponse:
    data = remote.dict(exclude_unset=True)

    return await RemoteApi.update(id, data)


@router.delete("/remotes/{id}/", dependencies=[Depends(requires_repo_admin)])
async def delete_remote(id: RemoteId) -> TaskResponse:
    return await RemoteApi.destroy(id)

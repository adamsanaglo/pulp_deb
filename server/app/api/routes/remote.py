from typing import Any, Optional

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


@router.get("/remotes/", response_model=RemoteListResponse)
async def list_remotes(
    pagination: Pagination = Depends(Pagination), name: Optional[str] = None
) -> Any:
    return await RemoteApi.list(pagination, params={"name": name})


@router.post(
    "/remotes/", response_model=RemoteResponse, dependencies=[Depends(requires_repo_admin)]
)
async def create_remote(remote: RemoteCreate) -> Any:
    return await RemoteApi.create(remote.dict(exclude_unset=True))


@router.get("/remotes/{id}/", response_model=RemoteResponse)
async def read_remote(id: RemoteId) -> Any:
    return await RemoteApi.read(id)


@router.patch(
    "/remotes/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def update_remote(id: RemoteId, remote: RemoteUpdate) -> Any:
    data = remote.dict(exclude_unset=True)

    return await RemoteApi.update(id, data)


@router.delete(
    "/remotes/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def delete_remote(id: RemoteId) -> Any:
    return await RemoteApi.destroy(id)

import logging
from typing import Any

from fastapi import APIRouter, Depends

from core.schemas import (
    PackageListResponse,
    Pagination,
    RepoId,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryPackageUpdate,
    RepositoryResponse,
    RepositoryUpdate,
    TaskResponse,
)
from services.pulp.api import PackageApi, RepositoryApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/", response_model=RepositoryListResponse)
async def list_repos(pagination: Pagination = Depends(Pagination)) -> Any:
    async with RepositoryApi() as api:
        return await api.list(pagination)


@router.post("/repositories/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate) -> Any:
    async with RepositoryApi() as api:
        return await api.create(repo.dict())


@router.get("/repositories/{id}/", response_model=RepositoryResponse)
async def read_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.read(id)


@router.patch("/repositories/{id}/", response_model=TaskResponse)
async def update_repository(id: RepoId, repo: RepositoryUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update(id, repo.dict(exclude_unset=True))


@router.delete("/repositories/{id}/", response_model=TaskResponse)
async def delete_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.destroy(id)


@router.get("/repositories/{id}/packages/", response_model=PackageListResponse)
async def get_packages(id: RepoId) -> Any:
    async with PackageApi() as api:
        return await api.repository_packages(id)


@router.patch("/repositories/{id}/packages/", response_model=TaskResponse)
async def update_packages(id: RepoId, repo_update: RepositoryPackageUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update_packages(id, **repo_update.dict())


@router.post("/repositories/{id}/publish/", response_model=TaskResponse)
async def publish_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.publish(id)

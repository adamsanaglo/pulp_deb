import logging
from typing import Any

from fastapi.requests import Request
from fastapi import APIRouter, Depends
from fastapi_microsoft_identity import requires_auth

from core.schemas import Pagination, RepoId, Repository, RepositoryPackageUpdate, RepositoryUpdate
from services.pulp.api import PackageApi, RepositoryApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/")
@requires_auth
async def list_repos(request: Request, pagination: Pagination = Depends(Pagination)) -> Any:
    async with RepositoryApi() as api:
        return await api.list(pagination)


@router.post("/repositories/")
@requires_auth
async def create_repository(request: Request, repo: Repository) -> Any:
    async with RepositoryApi() as api:
        return await api.create(repo.dict())


@router.get("/repositories/{id}/")
@requires_auth
async def read_repository(request: Request, id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.read(id)


@router.patch("/repositories/{id}/")
@requires_auth
async def update_repository(request: Request, id: RepoId, repo: RepositoryUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update(id, repo.dict(exclude_unset=True))


@router.delete("/repositories/{id}/")
@requires_auth
async def delete_repository(request: Request, id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.destroy(id)


@router.get("/repositories/{id}/packages/")
@requires_auth
async def get_packages(request: Request, id: RepoId) -> Any:
    async with PackageApi() as api:
        return await api.repository_packages(id)


@router.patch("/repositories/{id}/packages/")
@requires_auth
async def update_packages(request: Request, id: RepoId, repo_update: RepositoryPackageUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update_packages(id, **repo_update.dict())


@router.post("/repositories/{id}/publish/")
@requires_auth
async def publish_repository(request: Request, id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.publish(id)

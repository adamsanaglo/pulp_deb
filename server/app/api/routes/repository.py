import logging
from typing import Any, Optional

from fastapi import APIRouter

from core.schemas import RepoId, Repository, RepositoryPackageUpdate, RepositoryUpdate
from services.pulp.api import PackageApi, RepositoryApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/")
async def list_repos(name: Optional[str] = None) -> Any:
    params = dict()
    if name:
        params = {"name": name}

    async with RepositoryApi() as api:
        return await api.list(params)


@router.post("/repositories/")
async def create_repository(repo: Repository) -> Any:
    async with RepositoryApi() as api:
        return await api.create(repo.dict())


@router.get("/repositories/{id}/")
async def read_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.read(id)


@router.patch("/repositories/{id}/")
async def update_repository(id: RepoId, repo: RepositoryUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update(id, repo.dict(exclude_unset=True))


@router.delete("/repositories/{id}/")
async def delete_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.destroy(id)


@router.get("/repositories/{id}/packages/")
async def get_packages(id: RepoId) -> Any:
    async with PackageApi() as api:
        return await api.repository_packages(id)


@router.patch("/repositories/{id}/packages/")
async def update_packages(id: RepoId, repo_update: RepositoryPackageUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update_packages(**repo_update.dict())


@router.post("/repositories/{id}/publish/")
async def publish_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.publish(id)

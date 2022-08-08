import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_active_account, requires_repo_admin, requires_repo_permission
from app.core.db import get_session
from app.core.models import Account, OwnedPackage, RepoAccess, Role
from app.core.schemas import (
    PackageListResponse,
    Pagination,
    RepoId,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryPackageUpdate,
    RepositoryResponse,
    RepositoryUpdate,
    RepoType,
    TaskResponse,
)
from app.services.pulp.api import PackageApi, RepositoryApi

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/", response_model=RepositoryListResponse)
async def list_repos(pagination: Pagination = Depends(Pagination)) -> Any:
    async with RepositoryApi() as api:
        return await api.list(pagination)


@router.post(
    "/repositories/", response_model=RepositoryResponse, dependencies=[Depends(requires_repo_admin)]
)
async def create_repository(repo: RepositoryCreate) -> Any:
    async with RepositoryApi() as api:
        return await api.create(repo.dict())


@router.get("/repositories/{id}/", response_model=RepositoryResponse)
async def read_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.read(id)


@router.patch(
    "/repositories/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def update_repository(id: RepoId, repo: RepositoryUpdate) -> Any:
    async with RepositoryApi() as api:
        return await api.update(id, repo.dict(exclude_unset=True))


@router.delete(
    "/repositories/{id}/", response_model=TaskResponse, dependencies=[Depends(requires_repo_admin)]
)
async def delete_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.destroy(id)


@router.get("/repositories/{id}/packages/", response_model=PackageListResponse)
async def get_packages(id: RepoId, pagination: Pagination = Depends(Pagination)) -> Any:
    async with PackageApi() as api:
        return await api.repository_packages(id, pagination)


@router.patch("/repositories/{id}/packages/", response_model=TaskResponse)
async def update_packages(
    id: RepoId,
    repo_update: RepositoryPackageUpdate,
    account: Account = Depends(get_active_account),
    session: AsyncSession = Depends(get_session),
) -> Any:
    if id.type == RepoType.apt and not repo_update.release:
        raise HTTPException(
            status_code=422, detail="Release field is required for apt repositories."
        )
    elif id.type == RepoType.yum and repo_update.release:
        raise HTTPException(
            status_code=422, detail="Release field is not permitted for yum repositories."
        )

    # Repo Package Update permissions are complicated.
    # * Repo Admins and Publishers should be able to ADD packages if and only if they "own" packages
    #   of that name in this repo.
    #   * Publishers must have access to this repo to add a package.
    #   * When anyone adds a package, record that they added it so that they'll "own" updates.
    # * Repo Admins and Publishers should be able to REMOVE packages that they "own" in this repo.
    #   * Exception: Package Admins and Publishers that have the "operator" flag set for this repo
    #     can remove *any* package. The "operator" flag corresponds with the pseudo-role "Repo
    #     Operator" to support the Mariner team.

    # First we must convert the package *ids* sent to us into *names*.
    add_names, remove_names = set(), set()
    async with PackageApi() as api:
        if repo_update.add_packages:
            for add_id in repo_update.add_packages:
                add_names.add(await api.get_package_name(add_id))
        if repo_update.remove_packages:
            for remove_id in repo_update.remove_packages:
                remove_names.add(await api.get_package_name(remove_id))

    # Ensure that, if a Publisher, the account has access to this repo.
    statement = select(RepoAccess).where(
        RepoAccess.account_id == account.id, RepoAccess.repo_id == id
    )
    repo_perm = (await session.execute(statement)).one_or_none()
    # sqlalchemy returns things from `session.execute` wrapped in tuples, for legacy reasons
    if repo_perm:
        repo_perm = repo_perm[0]

    if account.role == Role.Publisher and not repo_perm:
        raise HTTPException(
            status_code=403,
            detail=f"Account {account.id} doesn't have permission to modify repo {id}",
        )

    # Create a mapping of package names to accounts that are allowed to modify them in this repo.
    package_name_to_account_id = defaultdict(set)
    statement = select(OwnedPackage).where(OwnedPackage.repo_id == id)
    for owned_package_tuple in await session.execute(statement):
        # sqlalchemy returns things from `session.execute` wrapped in tuples, for legacy reasons
        op = owned_package_tuple[0]
        package_name_to_account_id[op.package_name].add(op.account_id)

    # Next enforce package adding permissions
    if add_names and account.role not in (Role.Repo_Admin, Role.Publisher):
        raise HTTPException(status_code=403, detail=f"Account {account.id} is not a Publisher")

    for name in add_names:
        # No owners is fine; that means this is a new package and the account can upload it.
        # If there is at least one record then this account must be among the owners.
        account_owners = package_name_to_account_id[name]
        if not (len(account_owners) == 0 or account.id in account_owners):
            raise HTTPException(
                status_code=403,
                detail=f"Account {account.id} is not an owner of package {name} in repo {id}",
            )

        # remember package ownership
        if len(account_owners) == 0:
            session.add(OwnedPackage(account_id=account.id, repo_id=id, package_name=name))

    # Next enforce package removing permissions
    if remove_names:
        if account.role == Role.Package_Admin or (
            account.role == Role.Publisher and repo_perm and repo_perm.operator
        ):
            pass  # Account can remove whatever they want

        elif account.role not in (Role.Repo_Admin, Role.Publisher):
            raise HTTPException(status_code=403, detail=f"Account {account.id} is not a Publisher")

        else:
            for name in remove_names:
                if account.id not in package_name_to_account_id[name]:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Account {account.id} is not an owner of {name}",
                    )

    # Commit the newly added package ownership records, if any.
    await session.commit()

    async with RepositoryApi() as api:
        return await api.update_packages(id, **repo_update.dict())


@router.post(
    "/repositories/{id}/publish/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_repo_permission)],
)
async def publish_repository(id: RepoId) -> Any:
    async with RepositoryApi() as api:
        return await api.publish(id)

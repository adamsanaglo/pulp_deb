import logging
from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.auth import (
    get_active_account,
    requires_repo_admin,
    requires_repo_admin_or_migration,
    requires_repo_permission,
)
from app.core.config import settings
from app.core.db import AsyncSession, get_session
from app.core.models import Account, OwnedPackage, RepoAccess, Role
from app.core.schemas import (
    Pagination,
    PublishRequest,
    RemoteId,
    RepoId,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryPackageUpdate,
    RepositoryResponse,
    RepositoryUpdate,
    RepoType,
    TaskResponse,
)
from app.services.pulp.api import PackageApi, PublicationApi, RepositoryApi
from app.services.pulp.content_manager import ContentManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/", response_model=RepositoryListResponse)
async def list_repos(
    pagination: Pagination = Depends(Pagination),
    name: Optional[str] = None,
    name__contains: Optional[str] = None,
    name__icontains: Optional[str] = None,
) -> Any:
    params = {"name": name, "name__contains": name__contains, "name__icontains": name__icontains}
    async with RepositoryApi() as api:
        return await api.list(pagination, params=params)


@router.post(
    "/repositories/", response_model=RepositoryResponse, dependencies=[Depends(requires_repo_admin)]
)
async def create_repository(repo: RepositoryCreate) -> Any:
    async with RepositoryApi() as api:
        return await api.create(repo.dict(exclude_unset=True))


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


@router.post(
    "/repositories/{id}/sync/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_repo_admin_or_migration)],
)
async def sync_repository(id: RepoId, remote: Optional[RemoteId] = None) -> Any:
    async with RepositoryApi() as api:
        return await api.sync(id, remote)


@router.patch("/repositories/{id}/packages/", response_model=TaskResponse)
async def update_packages(
    id: RepoId,
    repo_update: RepositoryPackageUpdate,
    account: Account = Depends(get_active_account),
    session: AsyncSession = Depends(get_session),
) -> Any:
    if id.type == RepoType.yum and repo_update.release:
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
    repo_perm = (await session.exec(statement)).one_or_none()

    if account.role == Role.Publisher and not repo_perm:
        raise HTTPException(
            status_code=403,
            detail=f"Account {account.id} doesn't have permission to modify repo {id}",
        )

    # Create a mapping of package names to accounts that are allowed to modify them in this repo.
    package_name_to_account_id = defaultdict(set)
    statement = select(OwnedPackage).where(OwnedPackage.repo_id == id)
    for owned_package in await session.exec(statement):
        package_name_to_account_id[owned_package.package_name].add(owned_package.account_id)

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

        # TODO: [MIGRATE] remove this check
        elif account.role == Role.Migration:
            pass

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

    cm = ContentManager(id, repo_update.release, repo_update.component)
    resp = await cm.add_and_remove_packages(repo_update.add_packages, repo_update.remove_packages)

    # TODO: [MIGRATE] remove these lines
    from app.services.migration import remove_vcurrent_packages

    if settings.AF_QUEUE_ACTION_URL and repo_update.remove_packages and not repo_update.migration:
        await remove_vcurrent_packages(repo_update.remove_packages, id, repo_update.release)

    return resp


@router.post(
    "/repositories/{id}/publish/",
    response_model=TaskResponse,
    dependencies=[Depends(requires_repo_permission)],
)
async def publish_repository(id: RepoId, publish: Optional[PublishRequest] = None) -> Any:
    if not publish:
        publish = PublishRequest()

    async with RepositoryApi() as api:
        if not publish.force:
            # make sure there's not already a publication
            repo = await api.read(id)
            async with PublicationApi() as pub_api:
                pub_resp = await pub_api.list(params={"repository_version": repo["latest_version"]})
                if pub_resp["count"] > 0:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"{repo['name']} has already published. "
                            "Use 'force' to publish anyway."
                        ),
                    )

        return await api.publish(id)

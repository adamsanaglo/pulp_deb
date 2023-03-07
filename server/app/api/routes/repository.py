import logging
from collections import defaultdict
from typing import List, MutableSet, Optional, Union

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
    NoOpTask,
    Pagination,
    PublishRequest,
    RemoteId,
    RepoId,
    RepositoryBulkDelete,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryPackageUpdate,
    RepositoryResponse,
    RepositoryUpdate,
    RepoType,
    RpmRepositoryResponse,
    TaskResponse,
)
from app.services.pulp.api import PublicationApi, RepositoryApi
from app.services.pulp.content_manager import ContentManager
from app.services.pulp.package_lookup import package_lookup

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/repositories/", response_model_exclude_unset=True)
async def list_repos(
    pagination: Pagination = Depends(Pagination),
    name: Optional[str] = None,
    name__contains: Optional[str] = None,
    name__icontains: Optional[str] = None,
    ordering: Optional[str] = None,
) -> RepositoryListResponse:
    params = {
        "name": name,
        "name__contains": name__contains,
        "name__icontains": name__icontains,
        "ordering": ordering,
    }
    return await RepositoryApi.list(pagination, params=params)


@router.post("/repositories/", dependencies=[Depends(requires_repo_admin)])
async def create_repository(
    repo: RepositoryCreate,
) -> Union[RpmRepositoryResponse, RepositoryResponse]:
    return await RepositoryApi.create(repo.dict(exclude_unset=True))


@router.get("/repositories/{id}/")
async def read_repository(id: RepoId) -> Union[RpmRepositoryResponse, RepositoryResponse]:
    return await RepositoryApi.read(id)


@router.patch("/repositories/{id}/", dependencies=[Depends(requires_repo_admin)])
async def update_repository(id: RepoId, repo: RepositoryUpdate) -> TaskResponse:
    if id.type != RepoType.yum and "sqlite_metadata" in repo.__fields_set__:
        raise HTTPException(
            status_code=422, detail="sqlite_metadata is only permitted for yum repositories."
        )

    return await RepositoryApi.update(id, repo.dict(exclude_unset=True))


@router.delete("/repositories/{id}/", dependencies=[Depends(requires_repo_admin)])
async def delete_repository(id: RepoId) -> TaskResponse:
    return await RepositoryApi.destroy(id)


@router.post("/repositories/{id}/sync/", dependencies=[Depends(requires_repo_admin_or_migration)])
async def sync_repository(id: RepoId, remote: Optional[RemoteId] = None) -> TaskResponse:
    return await RepositoryApi.sync(id, remote)


@router.patch("/repositories/{id}/packages/")
async def update_packages(
    id: RepoId,
    repo_update: RepositoryPackageUpdate,
    account: Account = Depends(get_active_account),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    # First we must convert the package *ids* sent to us into *names*.
    add_names, remove_names = set(), set()
    remove_filenames: List[str] = []  # TODO: [MIGRATE] remove
    package_type = id.package_type
    if repo_update.add_packages:
        packages = await package_lookup(
            repo=id, release=repo_update.release, package_ids=repo_update.add_packages
        )
        add_names = {x[package_type.pulp_name_field] for x in packages}
        # TODO: [MIGRATE] remove
        # If someone is manipulating repo package associations in vNext we always want to remove the
        # packages in vCurrent. If we're removing packages from a repo then obviously we want to
        # mirror that change in vCurrent. However even if we're adding packages in vNext we want to
        # remove in vCurrent; this is because the package being added in vNext might be a different
        # build from the one in vCurrent but have the same NVA / NEVRA, and we don't want a future
        # sync to overwrite the copy that the Publisher explicitly added to the repo. Once
        # Publishers migrate to the vNext api / cli they should continue to use it, not switch back
        # and forth.
        remove_filenames.extend(
            [x[package_type.pulp_filename_field].split("/")[-1] for x in packages]
        )
        # END [MIGRATE]
    if repo_update.remove_packages:
        packages = await package_lookup(
            repo=id, release=repo_update.release, package_ids=repo_update.remove_packages
        )
        remove_names = {x[package_type.pulp_name_field] for x in packages}
        # TODO: [MIGRATE] remove
        remove_filenames.extend(
            [x[package_type.pulp_filename_field].split("/")[-1] for x in packages]
        )

    return await _update_packages(
        id,
        repo_update,
        account,
        session,
        add_names,
        remove_names,
        remove_filenames,
    )


@router.patch("/repositories/{id}/bulk_delete/")
async def bulk_delete(
    id: RepoId,
    delete_cmd: RepositoryBulkDelete,
    account: Account = Depends(get_active_account),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Essentially the same thing as passing a list of Package IDs to update_packages, except allows
    for a more optimized workflow because the caller does not have to look up the IDs first.
    Primarily this will be useful for handing bulk-deletes from the migration function (so lists
    of debs and rpms), but it will also allow for a "repo clear" command in the cli.
    """
    # We'll need to look up package ids.
    # We can also allow an "all" delete to clear every package in the repo without the caller
    # having to know anything about them. Pulp actually allows for a "*" special package id to be
    # passed to delete everything, but we can't use that here because it would bypass cookie-lick
    # restrictions in our downstream code. That also would wipe out all Releases / Components in
    # deb repos, which is probably not what the user intends.

    packages = await package_lookup(id, delete_cmd.release, package_queries=delete_cmd.packages)
    ids, names, filenames = [], set(), []
    name_field = id.package_type.pulp_name_field
    filename_field = id.package_type.pulp_filename_field
    for package in packages:
        ids.append(package["id"])
        names.add(package[name_field])
        # TODO: [MIGRATE] remove this
        filenames.append(package[filename_field].split("/")[-1])
        # END [MIGRATE]

    if not ids:
        # Nothing to delete found, probably previous request succeeded.
        # Return success for idempotence.
        return TaskResponse(task=NoOpTask.id)

    update_cmd = RepositoryPackageUpdate(
        remove_packages=ids,
        release=delete_cmd.release,
        component=delete_cmd.component,
        migration=delete_cmd.migration,  # TODO: [MIGRATE] remove this line
    )
    return await _update_packages(id, update_cmd, account, session, set(), names, filenames)


async def _update_packages(
    id: RepoId,
    repo_update: RepositoryPackageUpdate,
    account: Account,
    session: AsyncSession,
    add_names: MutableSet[str],
    remove_names: MutableSet[str],
    remove_filenames: List[str],  # TODO: [MIGRATE] remove
) -> TaskResponse:
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

    if (
        id.type in (RepoType.apt, RepoType.yum)
        and settings.AF_QUEUE_ACTION_URL
        and not repo_update.migration
    ):
        await remove_vcurrent_packages(remove_filenames, id, resp["task"], repo_update.release)
    # END [MIGRATE]

    return resp


@router.post("/repositories/{id}/publish/", dependencies=[Depends(requires_repo_permission)])
async def publish_repository(id: RepoId, publish: Optional[PublishRequest] = None) -> TaskResponse:
    if not publish:
        publish = PublishRequest()

    repo = await RepositoryApi.read(id)

    if not publish.force:
        # make sure there's not already a publication
        pub_resp = await PublicationApi.list(params={"repository_version": repo["latest_version"]})
        if pub_resp["count"] > 0:
            raise HTTPException(
                status_code=422,
                detail=(f"{repo['name']} has already published. " "Use 'force' to publish anyway."),
            )

    # the sqlite_metadata field on the repo is only used by Pulp when autopublishing but we'll
    # use it when creating an rpm publication
    if repo.get("sqlite_metadata", False):
        logging.warning(
            f"Warning: generating sqlite metadata for '{repo['name']}'. "
            "This feature is deprecated in Pulp."
        )
        data = dict(sqlite_metadata=True)
    else:
        data = {}

    return await RepositoryApi.publish(id, data)

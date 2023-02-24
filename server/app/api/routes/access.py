import re
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.core.db import AsyncSession, get_session
from app.core.models import Account, OwnedPackage, RepoAccess
from app.core.schemas import (
    AccountRepoPackagePermissionUpdate,
    AccountRepoPermissionUpdate,
    OwnedPackageResponse,
    Pagination,
    RepoAccessResponse,
    RepoId,
    RepositoryResponse,
)
from app.services.pulp.api import RepositoryApi

router = APIRouter()


async def _get_matching_repos(name_regex: str) -> List[Any]:
    ret = []
    page = Pagination()
    while True:
        response = await RepositoryApi.list(page)
        for repo in response["results"]:
            if re.match(name_regex, repo["name"]):
                ret.append(repo)
        page.offset += page.limit
        if page.offset >= response["count"]:
            break

    if len(ret) < 1:
        raise HTTPException(404, detail=f"Could not find repo(s) matching '{name_regex}'")

    return ret


async def _get_named_accounts(session: AsyncSession, account_names: List[str]) -> List[Account]:
    statement = select(Account).where(Account.name.in_(account_names))
    results = await session.exec(statement)
    accounts = list(results.all())
    if len(accounts) < 1:
        raise HTTPException(
            404, detail=f"Could not find account(s) matching '{(';').join(account_names)}'"
        )
    return accounts


# If you just do a get on /accounts/repo_access/ then it matches list_account and blows up.
@router.get("/access/repo/")
async def list_repo_access(
    session: AsyncSession = Depends(get_session),
    account: Optional[UUID] = None,
) -> List[RepoAccessResponse]:
    statement = select(RepoAccess)
    if account:
        statement = statement.where(RepoAccess.account_id == account)
    results = await session.exec(statement)
    return list(results.all())


@router.post("/access/repo/{id}/clone_from/{original_id}/")
async def clone_repo_access_from(
    id: RepoId,
    original_id: RepoId,
    session: AsyncSession = Depends(get_session),
) -> List[RepoAccessResponse]:
    """Additively clone the repo permissions from another repo."""
    statement = select(RepoAccess).where(RepoAccess.repo_id == id)
    current_perms = (await session.exec(statement)).all()
    current_perms_accounts = [x.account_id for x in current_perms]

    statement = select(RepoAccess).where(RepoAccess.repo_id == original_id)
    original_perms = (await session.exec(statement)).all()

    new_perms = []
    for perm in original_perms:
        if perm.account_id not in current_perms_accounts:
            new_perm = RepoAccess(account_id=perm.account_id, repo_id=id, operator=perm.operator)
            new_perms.append(new_perm)
            session.add(new_perm)

    await session.commit()
    return new_perms


@router.post("/access/repo/grant/")
async def grant_repo_access(
    update: AccountRepoPermissionUpdate,
    session: AsyncSession = Depends(get_session),
) -> List[RepositoryResponse]:
    repos = await _get_matching_repos(update.repo_regex)
    for account in await _get_named_accounts(session, update.account_names):
        for repo in repos:
            # don't create duplicate records
            statement = select(RepoAccess).where(
                RepoAccess.account_id == account.id, RepoAccess.repo_id == repo["id"]
            )
            repo_access = (await session.execute(statement)).one_or_none()
            if not repo_access:
                session.add(
                    RepoAccess(account_id=account.id, repo_id=repo["id"], operator=update.operator)
                )

    await session.commit()
    return repos


@router.post("/access/repo/revoke/")
async def revoke_repo_access(
    update: AccountRepoPermissionUpdate,
    session: AsyncSession = Depends(get_session),
) -> List[RepositoryResponse]:
    repos = await _get_matching_repos(update.repo_regex)
    for account in await _get_named_accounts(session, update.account_names):
        for repo in repos:
            statement = select(RepoAccess).where(
                RepoAccess.account_id == account.id, RepoAccess.repo_id == repo["id"]
            )
            repo_access = (await session.execute(statement)).one_or_none()
            if repo_access:
                await session.delete(repo_access[0])

    await session.commit()
    return repos


# If you just do a get on /accounts/package_ownership/ then it matches list_account and blows up.
@router.get("/access/package/")
async def list_package_ownership(
    session: AsyncSession = Depends(get_session), account: Optional[UUID] = None
) -> List[OwnedPackageResponse]:
    statement = select(OwnedPackage)
    if account:
        statement = statement.where(OwnedPackage.account_id == account)
    results = (await session.execute(statement)).all()
    return [x[0] for x in results]


@router.post("/access/package/grant/")
async def grant_package_ownership(
    update: AccountRepoPackagePermissionUpdate, session: AsyncSession = Depends(get_session)
) -> List[RepositoryResponse]:
    repos = await _get_matching_repos(update.repo_regex)
    accounts = await _get_named_accounts(session, update.account_names)
    for account in accounts:
        for repo in repos:
            for name in update.package_names:
                # don't create duplicate records
                statement = select(OwnedPackage).where(
                    OwnedPackage.account_id == account.id,
                    OwnedPackage.repo_id == repo["id"],
                    OwnedPackage.package_name == name,
                )
                op = (await session.execute(statement)).one_or_none()
                if not op:
                    session.add(
                        OwnedPackage(account_id=account.id, repo_id=repo["id"], package_name=name)
                    )

    await session.commit()
    return repos


@router.post("/access/package/revoke/")
async def revoke_package_ownership(
    update: AccountRepoPackagePermissionUpdate, session: AsyncSession = Depends(get_session)
) -> List[RepositoryResponse]:
    repos = await _get_matching_repos(update.repo_regex)
    accounts = await _get_named_accounts(session, update.account_names)
    for account in accounts:
        for repo in repos:
            for name in update.package_names:
                statement = select(OwnedPackage).where(
                    OwnedPackage.account_id == account.id,
                    OwnedPackage.repo_id == repo["id"],
                    OwnedPackage.package_name == name,
                )
                op = (await session.execute(statement)).one_or_none()
                if op:
                    await session.delete(op[0])

    await session.commit()
    return repos

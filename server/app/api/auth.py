from typing import Optional

import fastapi_microsoft_identity
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm.exc import NoResultFound
from sqlmodel import select

from app.core.db import AsyncSession, get_session
from app.core.models import Account, RepoAccess, Role
from app.core.schemas import RepoId

SUPPORT = "Contact your team's PMC Account Admin or PMC Support for assistance."


@fastapi_microsoft_identity.requires_auth  # type: ignore
async def authenticate(request: Request) -> Optional[Response]:
    """
    Does nothing but trigger requires_auth. The request arg must be passed as a kwarg.
    :returns: a 401 Response object if requires_auth fails to authenticate, else None.
    """
    return None


async def get_active_account(
    request: Request, session: AsyncSession = Depends(get_session)
) -> Account:
    """
    Authenticates the incoming request, looks them up in the db, and ensures the account is active.
    If any of these fail then raise an appropriate exception.
    """
    unauthenticated_response = await authenticate(request=request)
    if unauthenticated_response:
        raise HTTPException(status_code=401, detail=unauthenticated_response.body.decode("utf-8"))

    # oid is a UUID for an account that we get from Azure Active Directory.
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/access-tokens#payload-claims
    oid = fastapi_microsoft_identity.get_token_claims(request)["oid"]

    statement = select(Account).where(Account.oid == oid)
    try:
        results = await session.exec(statement)
        account = results.one()
    except NoResultFound:
        raise HTTPException(
            status_code=403, detail=f"Domain UUID {id} is not provisioned in PMC. {SUPPORT}"
        )

    if not account.is_enabled:
        raise HTTPException(status_code=403, detail=f"PMC access for {id} is disabled. {SUPPORT}")

    return account


async def requires_account_admin(account: Account = Depends(get_active_account)) -> None:
    if account.role != Role.Account_Admin:
        raise HTTPException(
            status_code=403, detail=f"Account {account.id} is not an Account Admin. {SUPPORT}"
        )


async def requires_repo_admin(account: Account = Depends(get_active_account)) -> None:
    if account.role != Role.Repo_Admin:
        raise HTTPException(
            status_code=403, detail=f"Account {account.id} is not a Repo Admin. {SUPPORT}"
        )


# TODO: [MIGRATE] Remove this function
async def requires_repo_admin_or_migration(account: Account = Depends(get_active_account)) -> None:
    if account.role not in [Role.Repo_Admin, Role.Migration]:
        raise HTTPException(
            status_code=403, detail=f"Account {account.id} is not a Repo Admin. {SUPPORT}"
        )


async def requires_package_admin(account: Account = Depends(get_active_account)) -> None:
    if account.role != Role.Package_Admin:
        raise HTTPException(
            status_code=403, detail=f"Account {account.id} is not a Package Admin. {SUPPORT}"
        )


async def requires_package_admin_or_publisher(
    account: Account = Depends(get_active_account),
) -> None:
    if account.role not in (Role.Package_Admin, Role.Publisher):
        raise HTTPException(
            status_code=403, detail=f"Account {account.id} is not a Publisher. {SUPPORT}"
        )


async def requires_repo_permission(
    id: RepoId,
    account: Account = Depends(get_active_account),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    For the routes that require this permission, Repo Admins can do whatever they want, and
    Publishers can do things only if they've been granted access to this repo.
    """
    if account.role == Role.Repo_Admin:
        return

    # TODO: [MIGRATE] Remove this if
    if account.role == Role.Migration:
        return

    if account.role == Role.Publisher:
        statement = select(RepoAccess).where(
            RepoAccess.account_id == account.id, RepoAccess.repo_id == id
        )
        if (await session.exec(statement)).one_or_none():
            return

    raise HTTPException(
        status_code=403, detail=f"Account {account.id} does not have access to repo {id}. {SUPPORT}"
    )

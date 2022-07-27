from typing import Optional

import fastapi_microsoft_identity
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
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
    id = fastapi_microsoft_identity.get_token_claims(request)["oid"]

    account = await session.get(Account, id)
    if not account:
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

    if account.role == Role.Publisher:
        statement = select(RepoAccess).where(
            RepoAccess.account_id == account.id, RepoAccess.repo_id == id
        )
        if (await session.execute(statement)).one_or_none():
            return

    raise HTTPException(
        status_code=403, detail=f"Account {account.id} does not have access to repo {id}. {SUPPORT}"
    )

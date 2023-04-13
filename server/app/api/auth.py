import re

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm.exc import NoResultFound
from sqlmodel import select

from app.core.config import settings
from app.core.db import AsyncSession, get_session
from app.core.models import Account, RepoAccess, Role
from app.core.schemas import RepoId

SUPPORT = "Contact your team's PMC Account Admin or PMC Support for assistance."
JWKS_URL = f"https://login.microsoftonline.com/{settings.TENANT_ID}/discovery/v2.0/keys"
ISSUERS = {
    "1.0": f"https://sts.windows.net/{settings.TENANT_ID}/",
    "2.0": f"https://login.microsoftonline.com/{settings.TENANT_ID}/v2.0",
}
ALGORITHMS = ["RS256"]


async def authenticate(request: Request) -> str:
    """Authenticate a request and return the oid."""
    jwks_client = jwt.PyJWKClient(JWKS_URL)
    auth_header = request.headers.get("Authorization", "")

    # parse the auth token
    if not (match := re.match(r"^bearer\s+(.*)", auth_header, re.IGNORECASE)):
        raise HTTPException(status_code=401, detail="Missing or invalid auth token.")
    token = match.group(1)

    # find the signing key
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Failed to parse auth token: {e}.")
    except jwt.PyJWKClientError as e:
        # TODO: once this PR is released update this to catch PyJWKClientConnectionError
        # https://github.com/jpadilla/pyjwt/pull/876
        if "Fail to fetch data from the url" in str(e):
            # retry the request
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        else:
            raise HTTPException(status_code=401, detail=f"{e}")

    # get the issuer based on the token version
    try:
        unverified = jwt.decode(token, options={"require": ["ver"], "verify_signature": False})
        token_version = unverified["ver"]
        issuer = ISSUERS[token_version]
    except (KeyError, jwt.PyJWTError) as e:
        raise HTTPException(status_code=401, detail=f"Invalid/missing token version: {e}.")

    # decode and validate the token
    try:
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=settings.APP_CLIENT_ID,
            issuer=issuer,
            options={"require": ["exp", "aud", "iss"]},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failure: {e}.")

    try:
        assert isinstance(data["oid"], str)
        return data["oid"]
    except KeyError:
        raise HTTPException(status_code=401, detail="Missing or invalid oid format.")


async def get_active_account(
    request: Request, session: AsyncSession = Depends(get_session)
) -> Account:
    """
    Authenticates the incoming request, looks them up in the db, and ensures the account is active.
    If any of these fail then raise an appropriate exception.
    """
    # oid is a UUID for an account that we get from Azure Active Directory.
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/access-tokens#payload-claims
    oid = await authenticate(request)

    statement = select(Account).where(Account.oid == oid)
    try:
        results = await session.exec(statement)
        account = results.one()
    except NoResultFound:
        raise HTTPException(
            status_code=403, detail=f"Domain UUID {oid} is not provisioned in PMC. {SUPPORT}"
        )

    if not account.is_enabled:
        raise HTTPException(status_code=403, detail=f"PMC access for {oid} is disabled. {SUPPORT}")

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

from itertools import product
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.models import Account, OwnedPackage, RepoAccess, Role

from .utils import assert_expected_response, gen_account_attrs, gen_repo_attrs

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_repository_list(async_client: AsyncClient, repository_api, account):
    response = await async_client.get("/api/v4/repositories/")
    assert_expected_response(response, 200, repository_api.list)


async def test_roles_repository_create(async_client: AsyncClient, repository_api, account):
    response = await async_client.post("/api/v4/repositories/", json=gen_repo_attrs())
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, repository_api.create)


async def test_roles_repository_read(async_client: AsyncClient, repository_api, account):
    response = await async_client.get(f"/api/v4/repositories/repositories-deb-apt-{uuid4()}/")
    assert_expected_response(response, 200, repository_api.read)


async def test_roles_repository_update(async_client: AsyncClient, repository_api, account):
    response = await async_client.patch(
        f"/api/v4/repositories/repositories-deb-apt-{uuid4()}/", json={"name": "test"}
    )
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, repository_api.update)


async def test_roles_repository_delete(async_client: AsyncClient, repository_api, account):
    response = await async_client.delete(f"/api/v4/repositories/repositories-deb-apt-{uuid4()}/")
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, repository_api.destroy)


@pytest.mark.parametrize("repo_perm", (True, False))
async def test_roles_repository_publish(
    async_client, db_session, repository_api, account, repo_perm
):
    repo_id = f"repositories-deb-apt-{uuid4()}"
    db_session.add(account)
    if repo_perm:
        db_session.add(RepoAccess(account_id=account.id, repo_id=repo_id))

    response = await async_client.post(f"/api/v4/repositories/{repo_id}/publish/")

    expected_status = 403
    if account.role == Role.Repo_Admin or (account.role == Role.Publisher and repo_perm):
        expected_status = 200
    assert_expected_response(response, expected_status, repository_api.publish)


def _setup_repo_package(
    package_api, db_session, repo_id, package_name, account, repo_perm, package_perm
):
    """
    Set up the appropriate database state given the desired repo and package permissions and
    monkeypatch out the Pulp communication.
    """
    db_session.add(account)
    if repo_perm:
        repo_access = RepoAccess(account_id=account.id, repo_id=repo_id)
        if repo_perm == "operator":
            repo_access.operator = True
        db_session.add(repo_access)
    # package_perm == "none" is a no-op, don't add an OwnedPackage record
    if package_perm == "other":
        other_account = Account(**gen_account_attrs())
        perm = OwnedPackage(account_id=other_account.id, repo_id=repo_id, package_name=package_name)
        db_session.add(other_account)
        db_session.add(perm)
    elif package_perm == "me":
        perm = OwnedPackage(account_id=account.id, repo_id=repo_id, package_name=package_name)
        db_session.add(perm)

    package_api.get_package_name.return_value = package_name


@pytest.mark.parametrize("repo_perm, package_perm", product((True, False), ("none", "other", "me")))
async def test_roles_repository_add_package(
    async_client, db_session, account, repo_perm, package_perm, repository_api, package_api
):
    """
    This test runs a total of 24 times: once for every combination of role (4) * whether or not
    you've been granted repo access (2) * who "owns" the package (nobody, someone else, me) (3).
    """
    # set up db
    repo_id = f"repositories-deb-apt-{uuid4()}"
    package_id = f"content-deb-packages-{uuid4()}"
    package_name = "package-name-test"
    _setup_repo_package(
        package_api, db_session, repo_id, package_name, account, repo_perm, package_perm
    )

    # try it
    response = await async_client.patch(
        f"/api/v4/repositories/{repo_id}/packages/", json={"add_packages": [package_id]}
    )

    # see if permissions are correct
    expected_status = 403
    account_allowed = account.role == Role.Repo_Admin or (
        account.role == Role.Publisher and repo_perm
    )
    if account_allowed and package_perm in ("none", "me"):
        expected_status = 200
    assert_expected_response(response, expected_status, repository_api.update_packages)

    # ensure we're correctly remembering package ownership
    if expected_status == 200:
        statement = select(OwnedPackage).where(
            OwnedPackage.account_id == account.id,
            OwnedPackage.repo_id == repo_id,
            OwnedPackage.package_name == package_name,
        )
        assert (await db_session.execute(statement)).one_or_none()


@pytest.mark.parametrize(
    "repo_perm, package_perm",
    product((False, True, "operator"), ("none", "other", "me")),
)
async def test_roles_repository_remove_package(
    async_client, db_session, account, repo_perm, package_perm, repository_api, package_api
):
    """
    This test runs a total of 36 times: once for every combination of role (4) * whether or not
    you've been granted repo access and/or are an operator (3) * who "owns" the package (nobody,
    someone else, me) (3).
    """
    # set up db
    repo_id = f"repositories-deb-apt-{uuid4()}"
    package_id = f"content-deb-packages-{uuid4()}"
    package_name = "package-name-test"
    _setup_repo_package(
        package_api, db_session, repo_id, package_name, account, repo_perm, package_perm
    )

    # try it
    response = await async_client.patch(
        f"/api/v4/repositories/{repo_id}/packages/", json={"remove_packages": [package_id]}
    )

    # see if permissions are correct
    expected_status = 403
    if package_perm == "me" and (
        account.role == Role.Repo_Admin or (account.role == Role.Publisher and repo_perm)
    ):
        # can delete own packages
        expected_status = 200
    elif account.role == Role.Package_Admin or (
        account.role == Role.Publisher and repo_perm == "operator"
    ):
        # can delete all packages
        expected_status = 200

    assert_expected_response(response, expected_status, repository_api.update_packages)

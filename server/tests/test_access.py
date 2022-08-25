import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.models import Account, OwnedPackage, RepoAccess, Role
from app.core.schemas import RepoType

from .utils import assert_expected_response, gen_account_attrs, gen_pulp_repo_response

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


def _setup_repos(list_mock, db_session, user, user_has_access=False):
    publisher = Account(**gen_account_attrs(Role.Publisher))
    db_session.add(user)
    db_session.add(publisher)
    artful = gen_pulp_repo_response(RepoType.apt, "microsoft-ubuntu-artful-prod")
    bionic = gen_pulp_repo_response(RepoType.apt, "microsoft-ubuntu-bionic-prod")
    cosmic = gen_pulp_repo_response(RepoType.apt, "microsoft-ubuntu-cosmic-prod")
    fedora30 = gen_pulp_repo_response(RepoType.yum, "microsoft-fedora30-prod")
    list_mock.return_value = {"results": [artful, bionic, cosmic, fedora30], "count": 4}

    if user_has_access:
        db_session.add(RepoAccess(repo_id=artful["id"], account_id=publisher.id, operator=False))
        db_session.add(RepoAccess(repo_id=bionic["id"], account_id=publisher.id, operator=False))
        db_session.add(RepoAccess(repo_id=cosmic["id"], account_id=publisher.id, operator=False))
        db_session.add(RepoAccess(repo_id=fedora30["id"], account_id=publisher.id, operator=False))
    return publisher, artful, bionic, cosmic, fedora30


async def test_access_list_repo(async_client, db_session, account, repository_api):
    """Dual-purpose test, checks access perms on the method, and also response."""
    publisher, artful, bionic, cosmic, fedora30 = _setup_repos(
        repository_api.list, db_session, account, user_has_access=True
    )

    response = await async_client.get("/api/v4/access/repo/")

    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)
    if response.status_code == 200:
        repo_ids = [x["id"] for x in (artful, bionic, cosmic, fedora30)]
        for repo_access in response.json():
            assert repo_access["account_id"] == str(publisher.id)
            assert repo_access["repo_id"] in repo_ids
            assert repo_access["operator"] is False


async def test_roles_access_grant_repo(
    async_client: AsyncClient, db_session, account, repository_api
):
    _setup_repos(repository_api.list, db_session, account)
    params = {"account_names": [account.name], "repo_regex": ".*"}
    response = await async_client.post("/api/v4/access/repo/grant/", json=params)
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_access_revoke_repo(
    async_client: AsyncClient, db_session, account, repository_api
):
    _setup_repos(repository_api.list, db_session, account, user_has_access=True)
    params = {"account_names": [account.name], "repo_regex": ".*"}
    response = await async_client.post("/api/v4/access/repo/revoke/", json=params)
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_access_grant_repo(async_client, db_session, account_admin, repository_api):
    publisher, artful, bionic, _, _ = _setup_repos(repository_api.list, db_session, account_admin)
    # a duplicate object should not be created later
    db_session.add(RepoAccess(repo_id=artful["id"], account_id=publisher.id, operator=False))

    params = {
        "account_names": [publisher.name],
        "repo_regex": "^microsoft-ubuntu-(artful|bionic)-prod$",
    }
    response = await async_client.post("/api/v4/access/repo/grant/", json=params)

    # Should match and grant access to/return artful and bionic only
    assert_expected_response(response, 200, repository_api.list, 2)
    # flake8 isn't happy with this line because it assumes you should be doing "not" or "is False"
    # tests instead of "== False", but it's wrong in this case.
    statement = select(RepoAccess).where(
        RepoAccess.account_id == publisher.id,
        RepoAccess.operator == False,  # noqa
    )
    perms = (await db_session.execute(statement)).all()
    assert len(perms) == 2
    for perm in perms:
        assert perm[0].repo_id in (artful["id"], bionic["id"])


async def test_access_revoke_repo(async_client, db_session, account_admin, repository_api):
    publisher, artful, bionic, cosmic, fedora30 = _setup_repos(
        repository_api.list, db_session, account_admin, user_has_access=True
    )

    params = {
        "account_names": [publisher.name],
        "repo_regex": "^microsoft-ubuntu-(artful|bionic)-prod$",
    }
    response = await async_client.post("/api/v4/access/repo/revoke/", json=params)

    # Should match and revoke access to/return artful and bionic only
    assert_expected_response(response, 200, repository_api.list, 2)
    statement = select(RepoAccess).where(RepoAccess.account_id == publisher.id)
    perms = (await db_session.execute(statement)).all()
    assert len(perms) == 2
    for perm in perms:
        assert perm[0].repo_id in (cosmic["id"], fedora30["id"])


async def test_access_list_package(async_client, db_session, account, repository_api):
    """Dual-purpose test, checks access perms on the method, and also response."""
    publisher, artful, bionic, _, _ = _setup_repos(repository_api.list, db_session, account)
    db_session.add(OwnedPackage(repo_id=artful["id"], account_id=publisher.id, package_name="vim"))
    db_session.add(OwnedPackage(repo_id=bionic["id"], account_id=publisher.id, package_name="vim"))

    response = await async_client.get("/api/v4/access/package/")

    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)
    if response.status_code == 200:
        for owned_package in response.json():
            assert owned_package["account_id"] == str(publisher.id)
            assert owned_package["repo_id"] in (artful["id"], bionic["id"])
            assert owned_package["package_name"] == "vim"


async def test_roles_access_grant_package(
    async_client: AsyncClient, db_session, account, repository_api
):
    _setup_repos(repository_api.list, db_session, account)
    params = {"account_names": [account.name], "repo_regex": ".*", "package_names": ["vim"]}
    response = await async_client.post("/api/v4/access/package/grant/", json=params)
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_access_revoke_package(
    async_client: AsyncClient, db_session, account, repository_api
):
    _setup_repos(repository_api.list, db_session, account, user_has_access=True)
    params = {"account_names": [account.name], "repo_regex": ".*", "package_names": ["vim"]}
    response = await async_client.post("/api/v4/access/package/revoke/", json=params)
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_access_grant_package(async_client, db_session, account_admin, repository_api):
    publisher, artful, bionic, _, _ = _setup_repos(repository_api.list, db_session, account_admin)
    # A duplicate object should not be created later
    db_session.add(OwnedPackage(repo_id=artful["id"], account_id=publisher.id, package_name="vim"))

    params = {
        "account_names": [publisher.name],
        "repo_regex": "^microsoft-ubuntu-(artful|bionic)-prod$",
        "package_names": ["vim"],
    }
    response = await async_client.post("/api/v4/access/package/grant/", json=params)

    # Should match and grant access to/return artful and bionic only
    assert_expected_response(response, 200, repository_api.list, 2)
    statement = select(OwnedPackage).where(
        OwnedPackage.account_id == publisher.id, OwnedPackage.package_name == "vim"
    )
    perms = (await db_session.execute(statement)).all()
    assert len(perms) == 2
    for perm in perms:
        assert perm[0].repo_id in (artful["id"], bionic["id"])


async def test_access_revoke_package(async_client, db_session, account_admin, repository_api):
    publisher, artful, bionic, cosmic, fedora30 = _setup_repos(
        repository_api.list, db_session, account_admin, user_has_access=True
    )
    db_session.add(OwnedPackage(repo_id=artful["id"], account_id=publisher.id, package_name="vim"))
    db_session.add(OwnedPackage(repo_id=bionic["id"], account_id=publisher.id, package_name="vim"))
    db_session.add(OwnedPackage(repo_id=cosmic["id"], account_id=publisher.id, package_name="vim"))
    db_session.add(
        OwnedPackage(repo_id=fedora30["id"], account_id=publisher.id, package_name="vim")
    )

    params = {
        "account_names": [publisher.name],
        "repo_regex": "^microsoft-ubuntu-(artful|bionic)-prod$",
        "package_names": ["vim"],
    }
    response = await async_client.post("/api/v4/access/package/revoke/", json=params)

    # Should match and revoke access to/return artful and bionic only
    assert_expected_response(response, 200, repository_api.list, 2)
    statement = select(OwnedPackage).where(OwnedPackage.account_id == publisher.id)
    perms = (await db_session.execute(statement)).all()
    assert len(perms) == 2
    for perm in perms:
        assert perm[0].repo_id in (cosmic["id"], fedora30["id"])

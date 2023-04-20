from itertools import product
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from tests.conftest import get_async_mock

from app.api.routes import repository as repository_module
from app.core.models import Account, OwnedPackage, RepoAccess, Role
from app.core.schemas import RepoType

from .utils import (
    assert_expected_response,
    gen_account_attrs,
    gen_list_attrs,
    gen_package_attrs,
    gen_repo_attrs,
    gen_repo_id,
    gen_task_attrs,
)

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
    async_client, db_session, repository_api, publication_api, account, repo_perm
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
    monkeypatch,
    db_session,
    repo_id,
    package_name,
    account,
    repo_perm,
    package_perm,
    package_filename,
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

    monkeypatch.setattr(
        repository_module,
        "package_lookup",
        get_async_mock([{"name": package_name, "location_href": package_filename}]),
    )


@pytest.mark.parametrize("repo_perm, package_perm", product((True, False), ("none", "other", "me")))
async def test_roles_repository_add_package(
    async_client,
    db_session,
    account,
    repo_perm,
    package_perm,
    content_manager,
    monkeypatch,
):
    """
    This test runs a total of 24 times: once for every combination of role (4) * whether or not
    you've been granted repo access (2) * who "owns" the package (nobody, someone else, me) (3).
    """
    # set up db
    monkeypatch.setattr(
        content_manager, "add_and_remove_packages", get_async_mock(gen_task_attrs())
    )
    repo_id = f"repositories-rpm-rpm-{uuid4()}"
    package_id = f"content-rpm-packages-{uuid4()}"
    package_name = "package-name-test"
    package_filename = "package-filename-test"
    _setup_repo_package(
        monkeypatch,
        db_session,
        repo_id,
        package_name,
        account,
        repo_perm,
        package_perm,
        package_filename,
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
    assert_expected_response(response, expected_status, content_manager.add_and_remove_packages)

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
    product((False, True, "operator-disabled", "operator-enabled"), ("none", "other", "me")),
)
async def test_roles_repository_remove_package(
    async_client,
    db_session,
    account,
    repo_perm,
    package_perm,
    content_manager,
    monkeypatch,
):
    """
    This test runs a total of 48 times: once for every combination of role (4) * whether or not
    you've been granted repo access and/or are an operator (4) * who "owns" the package (nobody,
    someone else, me) (3).
    """
    superuser = False
    if type(repo_perm) is not bool:
        repo_perm, enabled = repo_perm.split("-")
        superuser = enabled == "enabled"
    # set up db
    monkeypatch.setattr(
        content_manager, "add_and_remove_packages", get_async_mock(gen_task_attrs())
    )
    repo_id = f"repositories-rpm-rpm-{uuid4()}"
    package_id = f"content-rpm-packages-{uuid4()}"
    package_name = "package-name-test"
    package_filename = "package-filename-test"
    _setup_repo_package(
        monkeypatch,
        db_session,
        repo_id,
        package_name,
        account,
        repo_perm,
        package_perm,
        package_filename,
    )

    # try it
    params = {"remove_packages": [package_id], "superuser": superuser}
    response = await async_client.patch(f"/api/v4/repositories/{repo_id}/packages/", json=params)

    # see if permissions are correct
    expected_status = 403
    if package_perm == "me" and (
        account.role == Role.Repo_Admin or (account.role == Role.Publisher and repo_perm)
    ):
        # can delete own packages
        expected_status = 200
    elif account.role == Role.Package_Admin or (
        account.role == Role.Publisher and repo_perm == "operator" and superuser
    ):
        # can delete all packages
        expected_status = 200

    assert_expected_response(response, expected_status, content_manager.add_and_remove_packages)


@pytest.mark.parametrize("repo_type", (RepoType.apt, RepoType.yum, RepoType.file, RepoType.python))
async def test_bulk_delete(
    async_client,
    package_api,
    repository_api,
    repo_type,
    monkeypatch,
):
    """This test confirms that the wiring works, most work is done in package_lookup."""
    monkeypatch.setattr(repository_module, "_update_packages", get_async_mock(gen_task_attrs()))
    package_type = repo_type.package_types[0]
    packages = [gen_package_attrs(package_type) for _ in range(3)]
    expected_ids = [x["id"] for x in packages]
    expected_names = {x[package_type.pulp_name_field] for x in packages}
    expected_filenames = {x[package_type.pulp_filename_field] for x in packages}
    package_api.list.side_effect = [gen_list_attrs([packages[i]]) for i in range(3)]
    repo_id = gen_repo_id(repo_type)

    await async_client.patch(
        f"/api/v4/repositories/{repo_id}/bulk_delete/", json={"packages": packages}
    )

    assert package_api.list.call_count == 3
    id, update_cmd, _, _, _, names, filenames = repository_module._update_packages.call_args.args
    assert id == repo_id
    assert names == expected_names
    assert set(filenames) == expected_filenames
    assert update_cmd.remove_packages == expected_ids

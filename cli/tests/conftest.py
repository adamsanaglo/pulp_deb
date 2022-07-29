import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional, Union

import pytest

from pmc.schemas import RepoType, Role

from .utils import (
    become,
    gen_account_attrs,
    gen_distro_attrs,
    gen_release_attrs,
    gen_repo_attrs,
    invoke_command,
)


@pytest.fixture(autouse=True)
def set_config() -> Path:
    settings = Path.cwd() / "tests" / "settings.toml"
    assert settings.is_file(), f"Could not find {settings}."
    os.environ["PMC_CLI_CONFIG"] = str(settings)
    return settings


@pytest.fixture(autouse=True)
def check_connection(set_config: Path) -> None:
    try:
        result = invoke_command(["repo", "list"])
        assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    except Exception as exc:
        raise Exception(f"{exc}. Is your server running?")


@contextmanager
def _object_manager(
    cmd: List[str], role: Role, cleanup_cmd: Union[List[str], None, bool] = None
) -> Generator[Any, None, None]:
    """
    Create, yield, and clean up an object given the command to create it and the Role that has
    permission.
    If "{type} delete {id}" does not suffice to clean it up you can pass a custom cleanup command.
    Pass "False" to perform no cleanup at all, not even "{type} delete {id}".
    """
    response = None
    try:
        become(role)
        result = invoke_command(cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            if cleanup_cmd is None:
                type = cmd[0]  # "repo", "distro", "account"
                cleanup_cmd = [type, "delete", response["id"]]
            if cleanup_cmd:
                become(role)  # again, because the test may have changed role.
                result = invoke_command(cleanup_cmd)
                assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture()
def repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs()
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd, Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def apt_repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs(RepoType.apt)
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd, Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def yum_repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs(RepoType.yum)
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd, Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def distro() -> Generator[Any, None, None]:
    become(Role.Repo_Admin)
    attrs = gen_distro_attrs()
    cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
    with _object_manager(cmd, Role.Repo_Admin) as d:
        yield d


@pytest.fixture()
def orphan_cleanup() -> Generator[None, None, None]:
    # We cannot simply delete content once created (Pulp doesn't have API for that) so instead
    # we must call the "orphan cleanup" api endpoint with a time of zero, forcing all orphans
    # (including our fixture-added content) to be cleaned up. This has a side effect of deleting
    # all other orphans from the database, so we should never run tests against a production db.
    try:
        yield
    finally:
        result = invoke_command(["orphan", "cleanup", "--protection-time", "0"])
        assert result.exit_code == 0, f"Failed to call orphan cleanup: {result.stderr}."


@pytest.fixture()
def release(orphan_cleanup: None, apt_repo: Any) -> Generator[Any, None, None]:
    # create the release
    attrs = gen_release_attrs()
    cmd = [
        "repo",
        "releases",
        "create",
        apt_repo["id"],
        attrs["distribution"],
        attrs["codename"],
        attrs["suite"],
        attrs["components"],
        attrs["architectures"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"

    # retrieve the release and yield it
    result = invoke_command(["repo", "releases", "list", apt_repo["id"]])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    release = json.loads(result.stdout)["results"][0]
    release["repository_id"] = apt_repo["id"]  # add repo id to response so tests can use it
    yield release


def _account_create_command() -> List[str]:
    p = gen_account_attrs()
    return [
        "account",
        "create",
        p["id"],
        p["name"],
        p["contact_email"],
        p["icm_service"],
        p["icm_team"],
    ]


@pytest.fixture()
def account_one() -> Generator[Any, None, None]:
    with _object_manager(_account_create_command(), Role.Account_Admin) as o:
        yield o


@pytest.fixture()
def account_two() -> Generator[Any, None, None]:
    """Generate multiple accounts."""
    with _object_manager(_account_create_command(), Role.Account_Admin) as o:
        yield o


def package_upload_command(package_name: str, unsigned: Optional[bool] = False) -> List[str]:
    package = Path.cwd() / "tests" / "assets" / package_name
    cmd = ["package", "upload", str(package)]

    # Required until https://github.com/pulp/pulp_rpm/pull/2537 is in current Pulp.
    if package.suffix == ".rpm":
        cmd.append("--force-name")

    if unsigned:
        cmd.append("--ignore-signature")

    return cmd


@contextmanager
def _package_manager(
    package_name: str, unsigned: Optional[bool] = False
) -> Generator[Any, None, None]:
    cmd = package_upload_command(package_name, unsigned)
    with _object_manager(cmd, Role.Package_Admin, False) as p:
        yield p


@pytest.fixture()
def deb_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.deb") as p:
        yield p


@pytest.fixture()
def zst_deb_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us-zst-compressed.deb") as p:
        yield p


@pytest.fixture()
def rpm_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.rpm") as p:
        yield p


@pytest.fixture()
def forced_unsigned_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("unsigned.rpm", unsigned=True) as p:
        yield p


@pytest.fixture()
def task() -> Generator[Any, None, None]:
    # do something, anything, that results in at least one task being created
    become(Role.Package_Admin)
    cmd = ["orphan", "cleanup"]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    yield response

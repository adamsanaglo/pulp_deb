import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

import pytest

from pmc.schemas import RepoType, Role

from .utils import (
    account_create_command,
    become,
    gen_distro_attrs,
    gen_release_attrs,
    gen_repo_attrs,
    invoke_command,
    repo_create_cmd,
)


@pytest.fixture(autouse=True, scope="session")
def set_config() -> Path:
    settings = Path.cwd() / "tests" / "settings.toml"
    assert settings.is_file(), f"Could not find {settings}."
    os.environ["PMC_CLI_CONFIG"] = str(settings)
    return settings


@pytest.fixture(autouse=True, scope="session")
def check_connection(set_config: Path) -> None:
    try:
        become(Role.Account_Admin)
        result = invoke_command(["account", "list"])
        assert result.exit_code == 0, f"account list failed: {result.stderr}"
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
    with _object_manager(repo_create_cmd(gen_repo_attrs()), Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def apt_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.apt)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def yum_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.yum)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def file_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.file)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def python_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.python)), Role.Repo_Admin) as r:
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
        become(Role.Package_Admin)
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
        attrs["name"],
        attrs["codename"],
        attrs["suite"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"

    # retrieve the release and yield it
    result = invoke_command(["repo", "releases", "list", apt_repo["id"]])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    release = json.loads(result.stdout)["results"][0]
    release["repository_id"] = apt_repo["id"]  # add repo id to response so tests can use it
    yield release


@pytest.fixture()
def account_one() -> Generator[Any, None, None]:
    with _object_manager(account_create_command(), Role.Account_Admin) as o:
        yield o


@pytest.fixture()
def account_two() -> Generator[Any, None, None]:
    """Generate multiple accounts."""
    with _object_manager(account_create_command(), Role.Account_Admin) as o:
        yield o


@pytest.fixture()
def repo_access(account_one: Dict[str, Any]) -> Generator[Any, None, None]:
    """Generate a repo access perm for account_one."""

    def _my_cmd(action: str) -> List[str]:
        return ["access", "repo", action, account_one["name"], "'.*'"]

    with _object_manager(_my_cmd("grant"), Role.Account_Admin, cleanup_cmd=_my_cmd("revoke")) as o:
        yield o


@pytest.fixture()
def package_access(account_one: Dict[str, Any]) -> Generator[Any, None, None]:
    """Generate a package access perm for account_one."""

    def _my_cmd(action: str) -> List[str]:
        return ["access", "package", action, account_one["name"], "'.*'", "vim"]

    with _object_manager(_my_cmd("grant"), Role.Account_Admin, cleanup_cmd=_my_cmd("revoke")) as o:
        yield o


def package_upload_command(
    package_name: str, unsigned: Optional[bool] = False, file_type: Optional[str] = None
) -> List[str]:
    package = Path.cwd() / "tests" / "assets" / package_name
    cmd = ["package", "upload", str(package)]

    if unsigned:
        cmd.append("--ignore-signature")

    if file_type:
        cmd += ["--type", file_type]

    return cmd


@contextmanager
def _package_manager(
    package_name: str, unsigned: Optional[bool] = False, file_type: Optional[str] = None
) -> Generator[Any, None, None]:
    cmd = package_upload_command(package_name, unsigned, file_type)
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
def file_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("hello.txt", file_type="file") as p:
        yield p


@pytest.fixture()
def python_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("helloworld-0.0.1-py3-none-any.whl") as p:
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

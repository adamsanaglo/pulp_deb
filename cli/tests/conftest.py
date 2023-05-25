import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

import pytest
import tomli
from xdist.scheduler.loadscope import LoadScopeScheduling  # type: ignore

from pmc.schemas import DistroType, RepoType, Role

from .utils import (
    account_create_command,
    gen_distro_attrs,
    gen_release_attrs,
    gen_repo_attrs,
    invoke_command,
    repo_create_cmd,
)


class CustomScheduler(LoadScopeScheduling):  # type: ignore
    """
    Running integration tests in parallel just does not tend to work very well, especially if they
    weren't designed for it, like these weren't. However if we only run three threads, and split
    the tests by module, sending repository and package tests to their own thread since they're
    the slowest, that seems to work _pretty_ well.
    """

    def _split_scope(self, nodeid):  # type: ignore
        if "test_repository.py" in nodeid:
            return "group1"
        if "test_package.py" in nodeid:
            return "group2"
        return "group3"


def pytest_xdist_make_scheduler(config, log):  # type: ignore
    """Use the pytest-xdist hook to tell it to use our custom scheduler."""
    return CustomScheduler(config, log)


@pytest.fixture(autouse=True, scope="session")
def config_file() -> Path:
    config_path = Path.cwd() / "tests" / "settings.toml"
    assert config_path.is_file(), f"Could not find {config_path}."
    os.environ["PMC_CLI_CONFIG"] = str(config_path)
    return config_path


@pytest.fixture(scope="session")
def settings(config_file: Path) -> Any:
    profiles = tomli.load(config_file.open("rb"))
    return next(iter(profiles.values()))


@pytest.fixture(autouse=True, scope="session")
def check_connection(config_file: Path) -> None:
    try:
        result = invoke_command(["account", "list"], role=Role.Account_Admin)
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
        result = invoke_command(cmd, role=role)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            if cleanup_cmd is None:
                type = cmd[0]  # "repo", "distro", "account"
                cleanup_cmd = [type, "delete", response["id"]]
            if cleanup_cmd:
                result = invoke_command(cleanup_cmd, role=role)
                assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture(scope="session")
def repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs()), Role.Repo_Admin) as r:
        yield r


@pytest.fixture(scope="session")
def apt_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.apt)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture()
def new_apt_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.apt)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture(scope="session")
def yum_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.yum)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture(scope="session")
def file_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.file)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture(scope="session")
def python_repo() -> Generator[Any, None, None]:
    with _object_manager(repo_create_cmd(gen_repo_attrs(RepoType.python)), Role.Repo_Admin) as r:
        yield r


@pytest.fixture(scope="session")
def distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs()
    cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
    with _object_manager(cmd, Role.Repo_Admin) as d:
        yield d


@pytest.fixture(scope="session")
def apt_distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs(DistroType.apt)
    cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
    with _object_manager(cmd, Role.Repo_Admin) as d:
        yield d


@pytest.fixture(scope="session")
def yum_distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs(DistroType.yum)
    cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
    with _object_manager(cmd, Role.Repo_Admin) as d:
        yield d


@pytest.fixture(scope="session")
def orphan_cleanup() -> Generator[None, None, None]:
    # We cannot simply delete content once created (Pulp doesn't have API for that) so instead
    # we must call the "orphan cleanup" api endpoint with a time of zero, forcing all orphans
    # (including our fixture-added content) to be cleaned up. This has a side effect of deleting
    # all other orphans from the database, so we should never run tests against a production db.
    try:
        yield
    finally:
        result = invoke_command(
            ["orphan", "cleanup", "--protection-time", "0"], role=Role.Package_Admin
        )
        assert result.exit_code == 0, f"Failed to call orphan cleanup: {result.stderr}."


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def account_one() -> Generator[Any, None, None]:
    with _object_manager(account_create_command(), Role.Account_Admin) as o:
        yield o


@pytest.fixture(scope="session")
def account_two() -> Generator[Any, None, None]:
    """Generate multiple accounts."""
    with _object_manager(account_create_command(), Role.Account_Admin) as o:
        yield o


@pytest.fixture(scope="session")
def repo_access(
    account_one: Dict[str, Any], apt_repo: Dict[str, Any]
) -> Generator[Any, None, None]:
    """Generate a repo access perm for account_one."""

    def _my_cmd(action: str) -> List[str]:
        return ["access", "repo", action, account_one["name"], apt_repo["name"]]

    # Cleaned up when the account is deleted
    with _object_manager(_my_cmd("grant"), Role.Account_Admin, cleanup_cmd=False) as o:
        yield o


@pytest.fixture(scope="session")
def package_access(
    account_one: Dict[str, Any], apt_repo: Dict[str, Any]
) -> Generator[Any, None, None]:
    """Generate a package access perm for account_one."""

    def _my_cmd(action: str) -> List[str]:
        return ["access", "package", action, account_one["name"], apt_repo["name"], "vim"]

    # Cleaned up when the account is deleted
    with _object_manager(_my_cmd("grant"), Role.Account_Admin, cleanup_cmd=False) as o:
        yield o


def package_upload_command(
    package_name: str,
    unsigned: Optional[bool] = False,
    file_type: Optional[str] = None,
    source_artifacts: Optional[List[str]] = None,
) -> List[str]:
    asset_path = Path.cwd() / "tests" / "assets"
    package = Path.cwd() / "tests" / "assets" / package_name
    cmd = ["package", "upload", str(asset_path / package)]

    if unsigned:
        cmd.append("--ignore-signature")

    if file_type:
        cmd += ["--type", file_type]

    if source_artifacts:
        for artifact in source_artifacts:
            cmd += ["--source-artifact", str(asset_path / artifact)]

    return cmd


@contextmanager
def _package_manager(
    package_name: str,
    unsigned: Optional[bool] = False,
    file_type: Optional[str] = None,
    source_artifacts: Optional[List[str]] = None,
) -> Generator[Any, None, None]:
    cmd = package_upload_command(package_name, unsigned, file_type, source_artifacts)
    with _object_manager(cmd, Role.Package_Admin, False) as p:
        yield p


@pytest.fixture(scope="session")
def deb_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.deb") as p:
        yield p[0]


@pytest.fixture(scope="session")
def deb_src_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager(
        "hello_2.10-2ubuntu2.dsc",
        True,
        source_artifacts=["hello_2.10.orig.tar.gz", "hello_2.10-2ubuntu2.debian.tar.xz"],
    ) as p:
        yield p[0]


@pytest.fixture(scope="session")
def zst_deb_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us-zst-compressed.deb") as p:
        yield p[0]


@pytest.fixture(scope="session")
def rpm_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.rpm") as p:
        yield p[0]


@pytest.fixture(scope="session")
def file_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("hello.txt", file_type="file") as p:
        yield p[0]


@pytest.fixture(scope="session")
def python_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("helloworld-0.0.1-py3-none-any.whl") as p:
        yield p[0]


@pytest.fixture(scope="session")
def forced_unsigned_package(orphan_cleanup: None) -> Generator[Any, None, None]:
    with _package_manager("unsigned.rpm", unsigned=True) as p:
        yield p[0]


@pytest.fixture(scope="session")
def task() -> Generator[Any, None, None]:
    # do something, anything, that results in at least one task being created
    cmd = ["orphan", "cleanup"]
    result = invoke_command(cmd, role=Role.Package_Admin)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    yield response

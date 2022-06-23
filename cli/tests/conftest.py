import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional

import pytest
from pmc.schemas import RepoType

from .utils import gen_distro_attrs, gen_publisher_attrs, gen_repo_attrs, invoke_command


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
    cmd: List[str], cleanup_cmd: Optional[List[str]] = None
) -> Generator[Any, None, None]:
    """
    Create, yield, and clean up an object given the command to create it.
    If "{type} delete {id}" does not suffice to clean it up you can pass a custom cleanup command.
    """
    response = None
    try:
        result = invoke_command(cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            if cleanup_cmd is None:
                type = cmd[0]  # "repo", "distro", "publisher"
                cleanup_cmd = [type, "delete", response["id"]]
            result = invoke_command(cleanup_cmd)
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture()
def repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs()
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd) as r:
        yield r


@pytest.fixture()
def apt_repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs(RepoType.apt)
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd) as r:
        yield r


@pytest.fixture()
def yum_repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs(RepoType.yum)
    cmd = ["repo", "create", attrs["name"], attrs["type"]]
    with _object_manager(cmd) as r:
        yield r


@pytest.fixture()
def distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs()
    cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
    with _object_manager(cmd) as d:
        yield d


@pytest.fixture()
def publisher() -> Generator[Any, None, None]:
    p = gen_publisher_attrs()
    cmd = ["publisher", "create", p["name"], p["contact_email"], p["icm_service"], p["icm_team"]]
    with _object_manager(cmd) as o:
        yield o


def package_upload_command(package_name: str) -> List[str]:
    package = Path.cwd() / "tests" / "assets" / package_name
    cmd = ["package", "upload", str(package)]

    # Required until https://github.com/pulp/pulp_rpm/pull/2537 is in current Pulp.
    if package.suffix == ".rpm":
        cmd.append("--force-name")

    return cmd


@contextmanager
def _package_manager(package_name: str) -> Generator[Any, None, None]:
    # We cannot simply delete packages once created (Pulp doesn't have API for that) so instead
    # we must call the "orphan cleanup" api endpoint with a time of zero, forcing all orphans
    # (including our fixture-added package) to be cleaned up. This has a side effect of deleting
    # all other orphans from the database, so we should never run tests against a production db.
    cmd = package_upload_command(package_name)
    cleanup_cmd = ["orphan", "cleanup", "--protection-time", "0"]
    with _object_manager(cmd, cleanup_cmd) as p:
        yield p


@pytest.fixture()
def deb_package() -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.deb") as p:
        yield p


@pytest.fixture()
def zst_deb_package() -> Generator[Any, None, None]:
    with _package_manager("signed-by-us-zst-compressed.deb") as p:
        yield p


@pytest.fixture()
def rpm_package() -> Generator[Any, None, None]:
    with _package_manager("signed-by-us.rpm") as p:
        yield p


@pytest.fixture()
def task() -> Generator[Any, None, None]:
    # do something, anything, that results in at least one task being created
    cmd = ["orphan", "cleanup"]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    yield response

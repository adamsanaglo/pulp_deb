from typing import Any

from pmc.schemas import Role
from tests.utils import become, invoke_command

# Note that create and delete are exercised by the fixture.


# grant and revoke exercised by the fixture
def test_list_repo_access(repo_access: Any) -> None:
    cmd = ["access", "repo", "list"]
    result = invoke_command(cmd)
    assert result.exit_code == 0


# test that the repo clone command correctly calls the server api
def test_clone_repo_access(apt_repo: Any, yum_repo: Any) -> None:
    become(Role.Account_Admin)
    cmd = ["access", "repo", "clone", apt_repo["id"], yum_repo["name"]]
    result = invoke_command(cmd)
    assert result.exit_code == 0


# grant and revoke exercised by the fixture
def test_list_package_ownership(package_access: Any) -> None:
    cmd = ["access", "package", "list"]
    result = invoke_command(cmd)
    assert result.exit_code == 0

from typing import Any

from tests.utils import invoke_command

# Note that create and delete are exercised by the fixture.


# grant and revoke exercised by the fixture
def test_list_repo_access(repo_access: Any) -> None:
    cmd = ["access", "repo", "list"]
    result = invoke_command(cmd)
    assert result.exit_code == 0


# grant and revoke exercised by the fixture
def test_list_package_ownership(package_access: Any) -> None:
    cmd = ["access", "package", "list"]
    result = invoke_command(cmd)
    assert result.exit_code == 0

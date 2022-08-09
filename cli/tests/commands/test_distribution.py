import json
from typing import Any

from tests.utils import gen_distro_attrs, invoke_command

# Note that create and delete are exercised by the fixture.


def test_create_with_repository(apt_repo: Any) -> None:
    attrs = gen_distro_attrs()
    cmd = [
        "distro",
        "create",
        attrs["name"],
        attrs["type"],
        attrs["base_path"],
        "--repository",
        apt_repo["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == attrs["name"]


def test_list(distro: Any) -> None:
    result = invoke_command(["distro", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert "count" in response
    assert response["count"] > 0


def test_show(distro: Any) -> None:
    result = invoke_command(["distro", "show", distro["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert distro["id"] == response["id"]


def test_duplicate_path(distro: Any) -> None:
    cmd = ["distro", "create", "pmc_cli_test_name", "apt", distro["base_path"]]
    result = invoke_command(cmd)

    assert result.exit_code != 0
    error = json.loads(result.stdout)
    assert "Invalid request" in error["message"]
    assert "This field must be unique." in error["details"]["base_path"]


def test_update(distro: Any) -> None:
    new_name = gen_distro_attrs()["name"]
    cmd = ["distro", "update", distro["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name

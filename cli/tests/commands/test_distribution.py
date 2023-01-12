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


def test_list_with_ordering(apt_distro: Any, yum_distro: Any) -> None:
    result = invoke_command(["distro", "list", "--ordering", "name"])
    assert result.exit_code == 0, f"distro list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) > 1
    assert response["results"][1]["name"] > response["results"][0]["name"]

    result = invoke_command(["distro", "list", "--ordering", "-name"])
    assert result.exit_code == 0, f"distro list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) > 1
    assert response["results"][1]["name"] < response["results"][0]["name"]


def test_show(distro: Any) -> None:
    result = invoke_command(["distro", "show", distro["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert distro["id"] == response["id"]


def test_show_with_name(distro: Any) -> None:
    result = invoke_command(["distro", "show", distro["name"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert distro["id"] == response["id"]


def test_duplicate_path(distro: Any) -> None:
    cmd = ["distro", "create", "pmc_cli_test_name", "apt", distro["base_path"]]
    result = invoke_command(cmd)

    assert result.exit_code != 0
    error = json.loads(result.stdout)
    assert "Bad Request" in error["message"]
    assert "This field must be unique." in error["detail"]["base_path"]


def test_update(distro: Any) -> None:
    new_name = gen_distro_attrs()["name"]
    cmd = ["distro", "update", distro["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name

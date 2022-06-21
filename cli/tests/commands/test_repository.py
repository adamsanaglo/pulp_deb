import json
from typing import Any

from tests.utils import gen_repo_attrs, invoke_command

# Note that create and delete are exercised by the fixture.


def test_list(repo: Any) -> None:
    result = invoke_command(["repo", "list"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert "count" in response
    assert response["count"] > 0


def test_paginated_list(yum_repo: Any, apt_repo: Any) -> None:
    result = invoke_command(["repo", "list", "--limit", "1"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1
    id = response["results"][0]["id"]

    result = invoke_command(["repo", "list", "--limit", "1", "--offset", "1"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1
    assert response["results"][0]["id"] != id


def test_show(repo: Any) -> None:
    result = invoke_command(["repo", "show", repo["id"]])
    assert result.exit_code == 0, f"repo show {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert repo["id"] == response["id"]


def test_update(repo: Any) -> None:
    new_name = gen_repo_attrs()["name"]
    cmd = ["repo", "update", repo["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"{cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def _update_list_packages(package: Any, repo: Any) -> None:
    # Note: Not a test. You can't just shove any package in any repo. See callers below.
    result = invoke_command(
        ["repo", "packages", "update", repo["id"], "--add-packages", package["id"]]
    )
    assert result.exit_code == 0, f"adding package to repo failed: {result.stderr}"

    result = invoke_command(["repo", "packages", "list", repo["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["count"] == 1
    assert response["results"][0]["id"] == package["id"]

    result = invoke_command(
        ["repo", "packages", "update", repo["id"], "--remove-packages", package["id"]]
    )
    assert result.exit_code == 0, f"removing package from repo failed: {result.stderr}"

    result = invoke_command(["repo", "packages", "list", repo["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["count"] == 0


def test_yum_update_list_packages(rpm_package: Any, yum_repo: Any) -> None:
    _update_list_packages(rpm_package, yum_repo)


def test_apt_update_list_packages(deb_package: Any, apt_repo: Any) -> None:
    _update_list_packages(deb_package, apt_repo)


def test_publish(repo: Any) -> None:
    result = invoke_command(["repo", "publish", repo["id"]])
    assert result.exit_code == 0, f"repo publish {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["state"] == "completed"

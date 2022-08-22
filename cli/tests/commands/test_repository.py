import json
from typing import Any, Optional

from pmc.schemas import Role
from tests.utils import become, gen_repo_attrs, invoke_command

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


def _update_list_packages(
    package_id: str, repo_id: str, release: Optional[str] = None, comp: Optional[str] = None
) -> None:
    # Note: Not a test. You can't just shove any package in any repo. See callers below.
    become(Role.Repo_Admin)
    cmd = ["repo", "packages", "update", repo_id, "--add-packages", package_id]
    if release and comp:
        cmd[4:4] = [release, comp]

    result = invoke_command(cmd)
    assert result.exit_code == 0, f"adding package to repo failed: {result.stderr}"

    result = invoke_command(["repo", "packages", "list", repo_id])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["count"] == 1
    assert response["results"][0]["id"] == package_id

    cmd = ["repo", "packages", "update", repo_id, "--remove-packages", package_id]
    if release and comp:
        cmd[4:4] = [release, comp]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"removing package from repo failed: {result.stderr}"

    result = invoke_command(["repo", "packages", "list", repo_id])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["count"] == 0


def test_yum_update_list_packages(rpm_package: Any, yum_repo: Any) -> None:
    _update_list_packages(rpm_package["id"], yum_repo["id"])


def test_apt_update_list_packages(deb_package: Any, release: Any) -> None:
    _update_list_packages(
        deb_package["id"],
        release["repository_id"],
        release["distribution"],
        release["components"][0],
    )


def test_apt_update_packages_without_release(deb_package: Any, release: Any) -> None:
    become(Role.Repo_Admin)
    cmd = [
        "repo",
        "packages",
        "update",
        release["repository_id"],
        "--add-packages",
        deb_package["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert error["detail"] == "Release field is required for apt repositories."


def test_yum_update_packages_with_release(rpm_package: Any, yum_repo: Any) -> None:
    become(Role.Repo_Admin)
    cmd = [
        "repo",
        "packages",
        "update",
        yum_repo["id"],
        "somerelease",
        "--add-packages",
        rpm_package["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert error["detail"] == "Release field is not permitted for yum repositories."


def test_publish(repo: Any) -> None:
    result = invoke_command(["repo", "publish", repo["id"]])
    assert result.exit_code == 0, f"repo publish {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["state"] == "completed"
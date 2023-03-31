import json
from collections import Counter
from typing import Any, List, Optional

from pmc.constants import LIST_SEPARATOR
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


def test_list_with_filters(yum_repo: Any, apt_repo: Any) -> None:
    result = invoke_command(["repo", "list", "--name", apt_repo["name"]])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1

    result = invoke_command(["repo", "list", "--name-contains", apt_repo["name"][2:-1]])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1

    result = invoke_command(["repo", "list", "--name-contains", apt_repo["name"][0:-2].upper()])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 0

    result = invoke_command(["repo", "list", "--name-icontains", apt_repo["name"][0:-2].upper()])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1


def test_list_with_ordering(apt_repo: Any, yum_repo: Any) -> None:
    result = invoke_command(["repo", "list", "--ordering", "name"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) > 1
    assert response["results"][1]["name"] > response["results"][0]["name"]

    result = invoke_command(["repo", "list", "--ordering", "-name"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) > 1
    assert response["results"][1]["name"] < response["results"][0]["name"]


def test_show(repo: Any) -> None:
    result = invoke_command(["repo", "show", repo["id"]])
    assert result.exit_code == 0, f"repo show {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert repo["id"] == response["id"]


def test_show_with_name(repo: Any) -> None:
    result = invoke_command(["repo", "show", repo["name"]])
    assert result.exit_code == 0, f"repo show {repo['name']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert repo["id"] == response["id"]


def test_update(repo: Any) -> None:
    new_name = gen_repo_attrs()["name"]
    cmd = ["repo", "update", repo["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"{cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def test_update_with_name(repo: Any) -> None:
    new_name = gen_repo_attrs()["name"]
    cmd = ["repo", "update", repo["name"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"{cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def _build_package_update_command(
    repo_id: str, package_ids: List[str], action: str, release: Optional[str] = None
) -> List[str]:
    cmd = [
        "repo",
        "packages",
        "update",
        repo_id,
        f"--{action}-packages",
        LIST_SEPARATOR.join(package_ids),
    ]
    if release:
        cmd[4:4] = [release]

    return cmd


def _build_package_list_command(repo_id: str, release: Optional[str] = None) -> List[str]:
    list_cmd = ["package", "package_type", "list", "--repo", repo_id]
    if release:
        list_cmd[5:5] = ["--release", release]

    return list_cmd


def _update_list_packages(
    package_ids: List[str], package_types: List[str], repo_id: str, release: Optional[str] = None
) -> None:
    # Note: Not a test. You can't just shove any package in any repo. See callers below.
    become(Role.Repo_Admin)
    add_cmd = _build_package_update_command(repo_id, package_ids, "add", release)
    list_cmd = _build_package_list_command(repo_id, release)

    result = invoke_command(add_cmd)
    assert result.exit_code == 0, f"adding package to repo failed: {result.stderr}"

    package_types_counter = Counter(package_types)
    for package_type, count in package_types_counter.items():
        list_cmd[1:2] = [package_type]
        result = invoke_command(list_cmd)
        assert result.exit_code == 0
        response = json.loads(result.stdout)
        assert response["count"] == count
        results = response["results"]
        for resp_result in results:
            id_index = package_ids.index(resp_result["id"])
            assert package_type == package_types[id_index]

    cmd = _build_package_update_command(repo_id, package_ids, "remove")
    result = invoke_command(cmd)
    assert result.exit_code == 0, f"removing package from repo failed: {result.stderr}"

    for package_type in package_types_counter.keys():
        list_cmd[1:2] = [package_type]
        result = invoke_command(list_cmd)
        assert result.exit_code == 0
        response = json.loads(result.stdout)
        assert response["count"] == 0


def test_yum_update_list_packages(rpm_package: Any, yum_repo: Any) -> None:
    _update_list_packages([rpm_package["id"]], ["rpm"], yum_repo["id"])


def test_apt_update_list_packages(deb_package: Any, release: Any) -> None:
    _update_list_packages(
        [deb_package["id"]],
        ["deb"],
        release["repository_id"],
        release["name"],
    )


def test_apt_update_list_source_packages(deb_src_package: Any, release: Any) -> None:
    _update_list_packages(
        [deb_src_package["id"]],
        ["debsrc"],
        release["repository_id"],
        release["name"],
    )


def test_apt_update_list_deb_and_debsrc_packages(
    deb_package: Any, deb_src_package: Any, release: Any
) -> None:
    _update_list_packages(
        [deb_src_package["id"], deb_package["id"]],
        ["debsrc", "deb"],
        release["repository_id"],
        release["name"],
    )


def test_apt_update_list_two_deb_packages(
    deb_package: Any, zst_deb_package: Any, release: Any
) -> None:
    _update_list_packages(
        [zst_deb_package["id"], deb_package["id"]],
        ["deb", "deb"],
        release["repository_id"],
        release["name"],
    )


def test_apt_update_list_python_and_rpm_packages(
    python_package: Any, rpm_package: Any, yum_repo: Any
) -> None:
    become(Role.Repo_Admin)
    add_cmd = [
        "repo",
        "packages",
        "update",
        yum_repo["id"],
        "--add-packages",
        f"{python_package['id']},{rpm_package['id']}",
    ]
    result = invoke_command(add_cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert error["detail"] == "All packages must be of homogeneous types."


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
    assert error["detail"] == "You must specify a release to add packages to an apt repo."


def test_apt_update_packages_with_bad_release(deb_package: Any, release: Any) -> None:
    become(Role.Repo_Admin)
    cmd = [
        "repo",
        "packages",
        "update",
        release["repository_id"],
        "bad_release",
        "--add-packages",
        deb_package["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert "Found 0 releases for 'bad_release'" in error["detail"]


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


def test_update_packages_invalid(yum_repo: Any) -> None:
    become(Role.Repo_Admin)

    # bad id
    cmd = [
        "repo",
        "packages",
        "update",
        yum_repo["id"],
        "--add-packages",
        "bad_id",
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert "invalid id" in result.stdout

    # no ids
    cmd = [
        "repo",
        "packages",
        "update",
        yum_repo["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    error = json.loads(result.stdout)
    assert error["http_status"] == 422
    assert "add_packages and remove_packages cannot both be empty" in result.stdout


def test_publish(repo: Any) -> None:
    result = invoke_command(["repo", "publish", repo["id"]])
    assert result.exit_code == 0, f"repo publish {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["state"] == "completed"


def test_publish_with_name(repo: Any) -> None:
    result = invoke_command(["repo", "publish", repo["name"]])
    assert result.exit_code == 0, f"repo publish {repo['name']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["state"] == "completed"


def test_republish(repo: Any) -> None:
    # first one succeeds
    result = invoke_command(["repo", "publish", repo["id"]])
    assert result.exit_code == 0, f"repo publish {repo['id']} failed: {result.stderr}"

    # second one fails
    result = invoke_command(["repo", "publish", repo["id"]])
    assert result.exit_code != 0
    response = json.loads(result.stdout)
    assert 422 == response["http_status"]

    # republish with force
    result = invoke_command(["repo", "publish", "--force", repo["name"]])
    assert result.exit_code == 0, f"repo publish {repo['name']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["state"] == "completed"


def test_retain_repo_versions(repo: Any) -> None:
    result = invoke_command(["repo", "update", repo["name"], "--retain-repo-versions", "1"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["retain_repo_versions"] == 1

    result = invoke_command(["repo", "update", repo["name"], "--retain-repo-versions", "abc"])
    assert result.exit_code != 0
    assert "not a valid int" in result.stderr

    result = invoke_command(["repo", "update", repo["name"], "--retain-repo-versions", ""])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["retain_repo_versions"] is None


def test_purge(yum_repo: Any, rpm_package: Any) -> None:
    repo_id = yum_repo["id"]
    become(Role.Repo_Admin)
    invoke_command(["repo", "packages", "update", repo_id, "--add-packages", rpm_package["id"]])
    # Assert has content
    result = invoke_command(["package", "rpm", "list", "--repo", repo_id])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert "count" in response
    assert response["count"] > 0

    # purge repo
    result = invoke_command(["repo", "purge", repo_id, "--confirm"])
    assert result.exit_code == 0, f"repo purge failed: {result.stderr}"

    # Assert has no content
    result = invoke_command(["package", "rpm", "list", "--repo", repo_id])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert "count" in response
    assert response["count"] == 0

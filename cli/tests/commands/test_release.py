import json
from typing import Any

from pmc.schemas import RepoType, Role
from tests.utils import become, gen_release_attrs, gen_repo_attrs, invoke_command, repo_create_cmd


def test_create_with_comps_architectures(orphan_cleanup: None, apt_repo: Any) -> None:
    attrs = gen_release_attrs()
    cmd = [
        "repo",
        "releases",
        "create",
        apt_repo["id"],
        attrs["name"],
        attrs["codename"],
        attrs["suite"],
        "--components",
        "test1,test2",
        "--architectures",
        "flux,",
    ]

    result = invoke_command(cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"

    # retrieve the release and yield it
    result = invoke_command(["repo", "releases", "list", apt_repo["id"]])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    release = json.loads(result.stdout)["results"][0]
    assert sorted(release["components"]), ["test1", "test2"]
    assert release["architectures"], ["flux"]


def test_list(release: Any) -> None:
    """Test release list command."""
    result = invoke_command(["repo", "releases", "list", release["repository_id"], "--limit", "1"])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1

    rel = response["results"][0]
    assert rel["components"] == ["main"]
    assert sorted(rel["architectures"]) == ["amd64", "arm64", "armhf"]

    result = invoke_command(["repo", "releases", "list", release["repository_id"], "--offset", "2"])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 0


def test_yum_release(yum_repo: Any) -> None:
    """Test that creating a release for a yum repo fails."""
    attrs = gen_release_attrs()
    cmd = [
        "repo",
        "releases",
        "create",
        yum_repo["id"],
        attrs["name"],
        attrs["codename"],
        attrs["suite"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    assert json.loads(result.stdout)["http_status"] == 422


def test_dupe_release(release: Any) -> None:
    """Check that attempting to create a duplicate release fails."""
    cmd = [
        "repo",
        "releases",
        "create",
        release["repository_id"],
        release["name"],
        release["codename"],
        release["suite"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    assert json.loads(result.stdout)["http_status"] == 409


def test_dupe_release_another_repo(release: Any) -> None:
    """Check that attempting to create a duplicate release for another repo succeeds."""
    repo = dict()
    try:
        # create another repo
        result = invoke_command(repo_create_cmd(gen_repo_attrs(RepoType.apt)))
        repo = json.loads(result.stdout)

        # create the same release for the new repo
        cmd = [
            "repo",
            "releases",
            "create",
            repo["id"],
            release["name"],
            release["codename"],
            release["suite"],
        ]
        result = invoke_command(cmd)
        assert result.exit_code == 0
    finally:
        if "id" in repo:
            invoke_command(["repo", "delete", repo["id"]])


def test_remove_releases(apt_repo: Any, deb_package: Any) -> None:
    become(Role.Repo_Admin)
    cmd = [
        "repo",
        "release",
        "create",
        apt_repo["id"],
    ]
    result = invoke_command(cmd + ["jammy"])
    assert result.exit_code == 0
    result = invoke_command(cmd + ["kinetic"])
    assert result.exit_code == 0

    # add a package to jammy
    cmd = [
        "repo",
        "packages",
        "update",
        apt_repo["id"],
        "jammy",
        "--add-packages",
        deb_package["id"],
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    result = invoke_command(["package", "deb", "list", "--repo", apt_repo["id"]])
    assert json.loads(result.stdout)["count"] == 1

    # remove kinetic. repo should still have the package and jammy release.
    result = invoke_command(["repo", "release", "delete", apt_repo["id"], "kinetic"])
    assert result.exit_code == 0

    result = invoke_command(["repo", "release", "list", apt_repo["id"]])
    assert json.loads(result.stdout)["count"] == 1

    result = invoke_command(["package", "deb", "list", "--repo", apt_repo["id"]])
    assert json.loads(result.stdout)["count"] == 1

    # now remove jammy. repo should have no release, no packages.
    result = invoke_command(["repo", "release", "delete", apt_repo["id"], "jammy"])
    assert result.exit_code == 0

    result = invoke_command(["repo", "release", "list", apt_repo["id"]])
    assert json.loads(result.stdout)["count"] == 0

    result = invoke_command(["package", "deb", "list", "--repo", apt_repo["id"]])
    assert json.loads(result.stdout)["count"] == 0

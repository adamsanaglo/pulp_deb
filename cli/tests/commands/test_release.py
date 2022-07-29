import json
from typing import Any

from pmc.schemas import RepoType
from tests.utils import gen_release_attrs, gen_repo_attrs, invoke_command


def test_list(release: Any) -> None:
    """Test release list command."""
    result = invoke_command(["repo", "releases", "list", release["repository_id"], "--limit", "1"])
    assert result.exit_code == 0, f"release list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1

    rel = response["results"][0]
    assert sorted(rel["components"]) == sorted(["main", "contrib", "non-free"])
    assert sorted(rel["architectures"]) == sorted(["arm", "amd64"])

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
        attrs["distribution"],
        attrs["codename"],
        attrs["suite"],
        attrs["components"],
        attrs["architectures"],
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
        release["distribution"],
        release["codename"],
        release["suite"],
        "main",
        "arm",
    ]
    result = invoke_command(cmd)
    assert result.exit_code == 1
    assert json.loads(result.stdout)["http_status"] == 409


def test_dupe_release_another_repo(release: Any) -> None:
    """Check that attempting to create a duplicate release for another repo succeeds."""
    repo = dict()
    try:
        # create another repo
        attrs = gen_repo_attrs(RepoType.apt)
        repo_cmd = ["repo", "create", attrs["name"], attrs["type"]]
        result = invoke_command(repo_cmd)
        repo = json.loads(result.stdout)

        # create the same release for the new repo
        cmd = [
            "repo",
            "releases",
            "create",
            repo["id"],
            release["distribution"],
            release["codename"],
            release["suite"],
            "main",
            "arm",
        ]
        result = invoke_command(cmd)
        assert result.exit_code == 0
    finally:
        if "id" in repo:
            invoke_command(["repo", "delete", repo["id"]])

import json
from typing import Any

from pmc.schemas import Role
from tests.utils import become, invoke_command

# TODO: test cancelling tasks? This is a fundamentally difficult thing to do as an integration
# test (which all of these are), because it requires you to set up some long-running task in
# pulp that you then swoop in and cancel before it finishes. I'd say don't bother unless we
# decide we need a unit test suite too.


def test_list(task: Any) -> None:
    result = invoke_command(["task", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_filter_list(yum_repo: Any, rpm_package: Any) -> None:
    repo_id = yum_repo["id"]
    become(Role.Repo_Admin)
    resp = invoke_command(
        ["repo", "packages", "update", repo_id, "--add-packages", rpm_package["id"]]
    )
    repo_version_id = json.loads(resp.stdout)["created_resources"][0]
    result = invoke_command(["task", "list", "--created-resource", repo_version_id])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) == 1


def test_list_with_ordering(task: Any, apt_repo: Any) -> None:
    result = invoke_command(["task", "list", "--ordering", "started_at"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) > 1
    assert response["results"][-1]["started_at"] >= response["results"][0]["started_at"]

    result = invoke_command(["task", "list", "--ordering", "-started_at"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0
    assert response["results"][-1]["started_at"] <= response["results"][0]["started_at"]


def test_show(task: Any) -> None:
    result = invoke_command(["task", "show", task["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert task["id"] == response["id"]

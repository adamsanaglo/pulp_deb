import json
from typing import Any

from typer.testing import CliRunner

from pmc.main import app
from tests.utils import gen_repo_attrs

runner = CliRunner(mix_stderr=False)


def test_list(repo: Any) -> None:
    result = runner.invoke(app, ["repo", "list"])
    assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert "count" in response
    assert response["count"] > 0


def test_show(repo: Any) -> None:
    result = runner.invoke(app, ["repo", "show", repo["id"]])
    assert result.exit_code == 0, f"repo show {repo['id']} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert repo["id"] == response["id"]


def test_update(repo: Any) -> None:
    new_name = gen_repo_attrs()["name"]
    cmd = ["repo", "update", repo["id"], "--name", new_name]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, f"{cmd} failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["name"] == new_name

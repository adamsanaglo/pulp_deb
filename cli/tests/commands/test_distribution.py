import json
from typing import Any

from typer.testing import CliRunner

from pmc.main import app
from tests.utils import gen_distro_attrs

runner = CliRunner(mix_stderr=False)


def test_list(distro: Any) -> None:
    result = runner.invoke(app, ["distro", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    response = response[1]  # TODO: remove when we support /distributions/ endpoint
    assert "count" in response
    assert response["count"] > 0


def test_show(distro: Any) -> None:
    result = runner.invoke(app, ["distro", "show", distro["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert distro["id"] == response["id"]


def test_update(distro: Any) -> None:
    new_name = gen_distro_attrs()["name"]
    cmd = ["distro", "update", distro["id"], "--name", new_name]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name

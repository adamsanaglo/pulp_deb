import json
from typing import Any

from typer.testing import CliRunner

from pmc.main import app
from tests.utils import gen_publisher_attrs

runner = CliRunner(mix_stderr=False)


def test_list(publisher: Any) -> None:
    result = runner.invoke(app, ["publisher", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_show(publisher: Any) -> None:
    result = runner.invoke(app, ["publisher", "show", publisher["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert publisher["id"] == response["id"]


def test_update(publisher: Any) -> None:
    new_name = gen_publisher_attrs()["name"]
    cmd = ["publisher", "update", publisher["id"], "--name", new_name]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def test_disable(publisher: Any) -> None:
    cmd = ["publisher", "update", publisher["id"], "--disabled"]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert not response["is_enabled"]

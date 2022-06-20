import json
from typing import Any

from tests.utils import gen_publisher_attrs, invoke_command


# Note that create and delete are exercised by the fixture.


def test_list(publisher: Any) -> None:
    result = invoke_command(["publisher", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_show(publisher: Any) -> None:
    result = invoke_command(["publisher", "show", publisher["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert publisher["id"] == response["id"]


def test_update(publisher: Any) -> None:
    new_name = gen_publisher_attrs()["name"]
    cmd = ["publisher", "update", publisher["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def test_disable(publisher: Any) -> None:
    cmd = ["publisher", "update", publisher["id"], "--disabled"]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert not response["is_enabled"]

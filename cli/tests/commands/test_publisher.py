import json
from typing import Any

from tests.utils import gen_publisher_attrs, invoke_command

# Note that create and delete are exercised by the fixture.


def test_list(publisher_one: Any, publisher_two: Any) -> None:
    result = invoke_command(["publisher", "list", "--limit", "2"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) == 2
    assert response["count"] >= 2
    assert response["offset"] == 0


def test_duplicate(publisher_one: Any) -> None:
    cmd = [
        "publisher",
        "create",
        publisher_one["name"],
        "dd@contoso.com",
        "contoso_test",
        "contoso",
    ]
    result = invoke_command(cmd)
    response = json.loads(result.stdout)
    assert result.exit_code != 0
    assert response["http_status"] == 409
    assert list(response["details"].keys()) == ["name"]
    assert response["details"]["name"] == ["This field must be unique."]


def test_show(publisher_one: Any) -> None:
    result = invoke_command(["publisher", "show", publisher_one["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert publisher_one["id"] == response["id"]


def test_update(publisher_one: Any) -> None:
    new_name = gen_publisher_attrs()["name"]
    cmd = ["publisher", "update", publisher_one["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def test_disable(publisher_one: Any) -> None:
    cmd = ["publisher", "update", publisher_one["id"], "--disabled"]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert not response["is_enabled"]

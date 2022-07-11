import json
from typing import Any

from tests.utils import gen_account_attrs, invoke_command

# Note that create and delete are exercised by the fixture.


def test_list(account_one: Any, account_two: Any) -> None:
    result = invoke_command(["account", "list", "--limit", "2"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) == 2
    assert response["count"] >= 2
    assert response["offset"] == 0


def test_duplicate_name(account_one: Any) -> None:
    cmd = [
        "account",
        "create",
        gen_account_attrs()["id"],
        account_one["name"],
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


def test_show(account_one: Any) -> None:
    result = invoke_command(["account", "show", account_one["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert account_one["id"] == response["id"]


def test_update(account_one: Any) -> None:
    new_name = gen_account_attrs()["name"]
    cmd = ["account", "update", account_one["id"], "--name", new_name]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new_name


def test_disable(account_one: Any) -> None:
    cmd = ["account", "update", account_one["id"], "--disabled"]
    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert not response["is_enabled"]

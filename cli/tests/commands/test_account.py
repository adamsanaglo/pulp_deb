import json
from typing import Any

from pmc.schemas import Role
from tests.utils import account_create_command, gen_account_attrs, invoke_command

# Note that create and delete are exercised by the fixture.


def test_list(account_one: Any, account_two: Any) -> None:
    result = invoke_command(["account", "list", "--limit", "2"], role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) == 2
    assert response["count"] >= 2
    assert response["offset"] == 0


def test_list_with_ordering(account_one: Any, account_two: Any) -> None:
    result = invoke_command(["account", "list", "--ordering", "name"], role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) > 0
    assert response["results"][1]["name"] > response["results"][0]["name"]

    # Descending
    result = invoke_command(["account", "list", "--ordering", "-name"], role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response["results"]) > 0
    assert response["results"][1]["name"] < response["results"][0]["name"]


def test_duplicate_name(account_one: Any) -> None:
    result = invoke_command(
        account_create_command(name=account_one["name"]), role=Role.Account_Admin
    )
    response = json.loads(result.stdout)
    assert result.exit_code != 0
    assert response["http_status"] == 409
    assert list(response["detail"].keys()) == ["name"]
    assert response["detail"]["name"] == ["This field must be unique."]


def test_duplicate_oid(account_one: Any) -> None:
    result = invoke_command(account_create_command(oid=account_one["oid"]), role=Role.Account_Admin)
    response = json.loads(result.stdout)
    assert result.exit_code != 0
    assert response["http_status"] == 409
    assert list(response["detail"].keys()) == ["oid"]
    assert response["detail"]["oid"] == ["This field must be unique."]


def test_show(account_one: Any) -> None:
    result = invoke_command(["account", "show", account_one["id"]], role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert account_one["id"] == response["id"]


def test_update(account_one: Any) -> None:
    new = gen_account_attrs()
    cmd = ["account", "update", account_one["id"], "--name", new["name"], "--oid", new["oid"]]
    result = invoke_command(cmd, role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["name"] == new["name"]
    assert response["oid"] == new["oid"]


def test_disable(account_one: Any) -> None:
    cmd = ["account", "update", account_one["id"], "--disabled"]
    result = invoke_command(cmd, role=Role.Account_Admin)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert not response["is_enabled"]

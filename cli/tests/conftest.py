import json
from typing import Any, Generator

import pytest
from typer.testing import CliRunner

from pmc.main import app

from .utils import gen_distro_attrs, gen_repo_attrs

runner = CliRunner(mix_stderr=False)


@pytest.fixture(autouse=True)
def check_connection() -> None:
    try:
        result = runner.invoke(app, ["repo", "list"])
        assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    except Exception as exc:
        raise Exception(f"{exc}. Is your server running?")


@pytest.fixture()
def repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs()
    response = None

    try:
        cmd = ["repo", "create", attrs["name"], attrs["type"]]
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            result = runner.invoke(app, ["repo", "delete", response["id"]])
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture()
def distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs()
    response = None

    try:
        cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["path"]]
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            result = runner.invoke(app, ["distro", "delete", response["id"]])
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."

import json
import os
from pathlib import Path
from typing import Any, Generator

import pytest
from typer.testing import CliRunner

from .utils import gen_distro_attrs, gen_publisher_attrs, gen_repo_attrs, invoke_command

runner = CliRunner(mix_stderr=False)


@pytest.fixture(autouse=True)
def set_config() -> Path:
    settings = Path.cwd() / "tests" / "settings.toml"
    assert settings.is_file(), f"Could not find {settings}."
    os.environ["PMC_CLI_CONFIG"] = str(settings)
    return settings


@pytest.fixture(autouse=True)
def check_connection(set_config: Path) -> None:
    try:
        result = invoke_command(["repo", "list"])
        assert result.exit_code == 0, f"repo list failed: {result.stderr}"
    except Exception as exc:
        raise Exception(f"{exc}. Is your server running?")


@pytest.fixture()
def repo() -> Generator[Any, None, None]:
    attrs = gen_repo_attrs()
    response = None

    try:
        cmd = ["repo", "create", attrs["name"], attrs["type"]]
        result = invoke_command(cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            result = invoke_command(["repo", "delete", response["id"]])
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture()
def distro() -> Generator[Any, None, None]:
    attrs = gen_distro_attrs()
    response = None

    try:
        cmd = ["distro", "create", attrs["name"], attrs["type"], attrs["base_path"]]
        result = invoke_command(cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            result = invoke_command(["distro", "delete", response["id"]])
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."


@pytest.fixture()
def publisher() -> Generator[Any, None, None]:
    attrs = gen_publisher_attrs()
    response = None

    try:
        cmd = [
            "publisher",
            "create",
            attrs["name"],
            attrs["contact_email"],
            attrs["icm_service"],
            attrs["icm_team"],
        ]
        result = invoke_command(cmd)
        assert result.exit_code == 0, f"Command {cmd} failed: {result.stderr}"
        response = json.loads(result.stdout)
        yield response
    finally:
        if response:
            result = invoke_command(["publisher", "delete", response["id"]])
            assert result.exit_code == 0, f"Failed to delete {response['id']}: {result.stderr}."
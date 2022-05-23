import json
import tempfile
from typing import Any

from typer.testing import CliRunner

from tests.utils import invoke_command

runner = CliRunner(mix_stderr=False)


def test_missing_config() -> None:
    result = invoke_command(["--config", "missing.json", "repo", "list"])
    assert result.exit_code == 1
    assert "does not exist" in result.stderr


def test_config_with_invalid_value() -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"no_wait": "invalid value"}, config)
    config.flush()
    result = invoke_command(["--config", config.name, "repo", "list"])
    assert result.exit_code == 1
    assert "validation error" in result.stderr


def test_config_id_only(repo: Any) -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"id_only": True}, config)
    config.flush()
    result = invoke_command(["--config", config.name, "repo", "show", repo["id"]])
    assert result.exit_code == 0
    assert result.stdout == repo["id"]

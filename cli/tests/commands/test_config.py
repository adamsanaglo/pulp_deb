import json
import tempfile
from typing import Any

from typer.testing import CliRunner

from pmc.main import app

runner = CliRunner(mix_stderr=False)


def test_missing_config() -> None:
    result = runner.invoke(app, ["--config", "missing.json", "repo", "list"])
    assert result.exit_code == 1
    assert "does not exist" in result.stderr


def test_config_with_invalid_value() -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"no_wait": "invalid value"}, config)
    config.flush()
    result = runner.invoke(app, ["--config", config.name, "repo", "list"])
    assert result.exit_code == 1
    assert "validation error" in result.stderr


def test_config_id_only(repo: Any) -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"id_only": True}, config)
    config.flush()
    result = runner.invoke(app, ["--config", config.name, "repo", "show", repo["id"]])
    assert result.exit_code == 0
    assert result.stdout == repo["id"]

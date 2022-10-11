import json
import tempfile
from typing import Any

import pytest

from tests.utils import invoke_command


def test_missing_config() -> None:
    result = invoke_command(["--config", "missing.json", "repo", "list"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_config_with_invalid_value() -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"no_wait": "invalid value"}, config)
    config.flush()
    result = invoke_command(["--config", config.name, "repo", "list"])
    assert result.exit_code == 1
    assert "ValidationError" in result.stdout


@pytest.mark.skip(reason="Authentication is required for all commands")
def test_config_id_only(repo: Any) -> None:
    config = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
    json.dump({"id_only": True}, config)
    config.flush()
    result = invoke_command(["--config", config.name, "repo", "show", repo["id"]])
    assert result.exit_code == 0
    assert result.stdout == repo["id"]

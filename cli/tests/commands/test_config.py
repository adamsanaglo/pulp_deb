import json
import tempfile
from re import search
from typing import Any

import tomli_w

from tests.utils import invoke_command


def test_missing_config() -> None:
    """Test a missing config."""
    result = invoke_command(["--config", "missing.json", "repo", "list"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_config_with_invalid_value() -> None:
    """Test a config wtih an invalid value."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as config:
        json.dump({"no_wait": "invalid value"}, config)
        config.flush()
        result = invoke_command(["--config", config.name, "repo", "list"])
        assert result.exit_code == 1
        assert "Missing or invalid option(s)" in result.stdout


def test_config_id_only(settings: Any, repo: Any) -> None:
    """Test setting id_only in the config."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as config:
        json.dump({**settings, **{"id_only": True}}, config)
        config.flush()
        result = invoke_command(["--config", config.name, "repo", "show", repo["id"]])
        assert result.exit_code == 0
        assert result.stdout == repo["id"]


def test_profiles(settings: Any, repo: Any) -> None:
    """Test a config with two profiles, one good and one bad."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml") as config:
        # create a config with two profiles: good and bad
        config.write(
            tomli_w.dumps(
                {"good": settings, "bad": {**settings, **{"msal_cert_path": "/bad/path/auth.pem"}}}
            )
        )
        config.flush()

        result = invoke_command(
            ["--config", config.name, "--profile", "good", "repo", "show", repo["id"]]
        )
        assert result.exit_code == 0
        assert "id" in result.stdout

        result = invoke_command(
            ["--config", config.name, "--profile", "bad", "repo", "show", repo["id"]]
        )
        search(r"file.*does not exist", result.stdout)
        assert result.exit_code != 0


def test_partial_config(settings: Any, repo: Any) -> None:
    """Test a config with only some values defined."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml") as config:
        config.write(tomli_w.dumps({"cli": {"no_wait": True}}))
        config.flush()

        result = invoke_command(
            [
                "--config",
                config.name,
                "--msal-client-id",
                settings["msal_client_id"],
                "--msal-scope",
                settings["msal_scope"],
                "--msal-cert-path",
                settings["msal_cert_path"],
                "--msal-authority",
                settings["msal_authority"],
                "repo",
                "show",
                repo["id"],
            ]
        )
        assert result.exit_code == 0
        assert "id" in result.stdout


def test_config_override(settings: Any, repo: Any) -> None:
    """Test that command line options will override the config."""
    result = invoke_command(
        [
            "--msal-client-id",
            "bad_client_id",
            "repo",
            "show",
            repo["id"],
        ]
    )
    assert result.exit_code != 0
    assert "AuthenticationError" in result.stdout


def test_invalid_toml() -> None:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml") as config:
        config.write("Hello World")
        config.flush()
        result = invoke_command(["--config", config.name, "repo", "list"])
        assert result.exit_code != 0
        assert "DecodeError: Parse error" in result.stdout

import json
from typing import Any, Dict
from uuid import uuid4

from click.testing import Result
from typer.testing import CliRunner

from pmc.main import app, format_exception
from pmc.schemas import DistroType, RepoType


def gen_repo_attrs() -> Dict[str, str]:
    return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=RepoType.apt)


def gen_distro_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_distro_{uuid4()}",
        type=DistroType.apt,
        base_path=f"{uuid4()}/{uuid4()}",
    )


def gen_publisher_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_publisher_{uuid4()}",
        contact_email="alice@contoso.com;bob@contoso.com",
        icm_service="test_icm_service",
        icm_team="test_icm_team",
    )


def invoke_command(runner: CliRunner, *args: Any, **kwargs: Any) -> Result:
    """
    Invoke a command and handle any exception that gets thrown.

    CliRunner calls the command directly which bypasses the error handling in main's run() function.
    This function emulates the logic in run() by appending the formatted error dict to
    result.stdout_bytes.
    """
    result = runner.invoke(app, *args, **kwargs)
    if result.exception:
        err = format_exception(result.exception)
        result.stdout_bytes += json.dumps(err).encode("utf-8")
    return result

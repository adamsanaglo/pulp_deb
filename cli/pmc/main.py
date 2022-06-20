import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import typer
from pydantic import AnyHttpUrl
from pydantic.tools import parse_obj_as

from .commands import config as config_cmd
from .commands import distribution, orphan, package, publisher, repository, task
from .context import PMCContext
from .schemas import CONFIG_PATHS, Config, Format
from .utils import PulpTaskFailure, parse_config, validate_config

app = typer.Typer()
app.add_typer(config_cmd.app, name="config")
app.add_typer(distribution.app, name="distro")
app.add_typer(package.app, name="package")
app.add_typer(repository.app, name="repo")
app.add_typer(task.app, name="task")
app.add_typer(publisher.app, name="publisher")
app.add_typer(orphan.app, name="orphan")


def _load_config(ctx: typer.Context, value: Optional[Path]) -> Optional[Path]:
    """Callback that attempts to load config."""
    path: Optional[Path] = None

    if value:
        if not value.is_file():
            raise ValueError(f"Error: file '{value}' does not exist or is not a file.")
        else:
            path = value
    else:
        path = next(filter(lambda fp: fp and fp.is_file(), CONFIG_PATHS), None)

    if path:
        try:
            config = parse_config(path)
            ctx.default_map = config.dict(exclude_unset=True)
        except Exception:
            # ignore parse exceptions for now. validate later once we can exclude config subcommands
            pass

    return path


def format_exception(exception: BaseException) -> Dict[str, Any]:
    """Build an error dict from an exception."""
    if isinstance(exception, httpx.HTTPStatusError):
        resp_json = exception.response.json()
        assert isinstance(resp_json, Dict)

        err = resp_json
        err["http_status"] = exception.response.status_code
        if "x-correlation-id" in exception.response.headers:
            err["correlation_id"] = exception.response.headers["x-correlation-id"]
    elif isinstance(exception, PulpTaskFailure):
        err = {
            "http_status": -1,
            "message": exception.original_message,
            "command_traceback": exception.original_traceback,
        }
        return err
    else:
        exc_message = type(exception).__name__
        if message := str(exception):
            exc_message += f": {message}"

        err = {
            "http_status": -1,
            "message": exc_message,
        }
        if isinstance(exception, httpx.RequestError):
            err["url"] = str(exception.request.url)

    err["command_traceback"] = "".join(traceback.format_tb(exception.__traceback__))
    return err


@app.callback()
def main(
    ctx: typer.Context,
    config_path: Path = typer.Option(
        None,
        "--config",
        "-c",
        callback=_load_config,
        help="Config file location. Defaults: \n" + ("\n").join(map(str, CONFIG_PATHS)),
        envvar="PMC_CLI_CONFIG",
    ),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for any background tasks."),
    no_color: bool = typer.Option(False, "--no-color", help="Suppress color output if enabled."),
    id_only: bool = typer.Option(False, "--id-only", help="Show ids instead of full responses."),
    resp_format: Format = typer.Option(Format.json, "--format", hidden=True),  # TODO: more formats
    base_url: str = typer.Option(""),
) -> None:
    if config_path and ctx.invoked_subcommand != "config":
        # validate config. allow users to still edit/recreate their config even if it's invalid.
        validate_config(config_path)

    config = Config(
        no_wait=no_wait,
        no_color=no_color,
        id_only=id_only,
        format=resp_format,
    )
    if base_url:
        config.base_url = parse_obj_as(AnyHttpUrl, base_url)

    ctx.obj = PMCContext(config=config, config_path=config_path)


def run() -> None:
    command = typer.main.get_command(app)

    try:
        command(standalone_mode=False)
    except Exception as exc:
        traceback.print_exc()
        typer.echo("")

        err = format_exception(exc)
        if sys.stdout.isatty():
            output = json.dumps(err, indent=3)
        else:
            output = str(err)
        typer.echo(output)

        exit(1)

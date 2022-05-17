import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
import typer

from .client import client
from .commands import config as config_cmd
from .commands import distribution, package, publisher, repository, task
from .schemas import CONFIG_PATHS, FINISHED_TASK_STATES, Format
from .utils import parse_config, validate_config

try:
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter
    from pygments.lexers import JsonLexer
except ImportError:
    PYGMENTS = False
else:
    PYGMENTS = True
    PYGMENTS_STYLE = "solarized-light"

TaskHandler = Optional[Callable[[str], Any]]


app = typer.Typer()
app.add_typer(config_cmd.app, name="config")
app.add_typer(distribution.app, name="distro")
app.add_typer(package.app, name="package")
app.add_typer(repository.app, name="repo")
app.add_typer(task.app, name="task")
app.add_typer(publisher.app, name="publisher")


@dataclass
class PMCContext:
    no_color: bool = False
    id_only: bool = False
    no_wait: bool = False
    format: str = "json"
    config_path: Optional[Path] = None
    isatty: bool = sys.stdout.isatty()

    @staticmethod
    def _extract_ids(resp_json: Any) -> Union[str, List[str], None]:
        if not isinstance(resp_json, dict):
            return None
        elif id := resp_json.get("id"):
            return str(id)
        elif task_id := resp_json.get("task"):
            return str(task_id)
        elif results := resp_json.get("results"):
            return [r["id"] for r in results]
        else:
            return None

    def poll_task(self, task_id: str, task_handler: TaskHandler = None) -> Any:
        resp = client.get(f"/tasks/{task_id}/")
        task = resp.json()

        if self.no_wait:
            return task

        typer.echo(f"Waiting for {task['id']}...", nl=False, err=True)

        while task["state"] not in FINISHED_TASK_STATES:
            sleep(1)
            resp = client.get(f"/tasks/{task['id']}/")
            task = resp.json()
            typer.echo(".", err=True, nl=False)

        typer.echo("", err=True)

        if task_handler:
            resp = task_handler(task)

        return resp

    def handle_response(self, resp: httpx.Response, task_handler: TaskHandler = None) -> None:
        if not resp.content:
            # empty response
            return

        if isinstance(resp.json(), dict) and (task_id := resp.json().get("task")):
            resp = self.poll_task(task_id, task_handler)

        if self.id_only and (id := self._extract_ids(resp.json())):
            typer.echo(id, nl=self.isatty)
        else:
            if not self.isatty:
                # do not format output if it's not going to a terminal
                typer.echo(json.dumps(resp.json()))
            else:
                output = json.dumps(resp.json(), indent=3)
                if PYGMENTS and not self.no_color:
                    formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
                    output = highlight(output, JsonLexer(), formatter)
                typer.echo(output)


def _load_config(ctx: typer.Context, value: Optional[Path]) -> Optional[Path]:
    """Callback that attempts to load config."""
    path: Optional[Path] = None

    if value:
        if not value.is_file():
            typer.echo(f"Error: file '{value}' does not exist or is not a file.", err=True)
            raise typer.Exit(code=1)
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
    elif isinstance(exception, httpx.RequestError):
        err = {
            "http_status": -1,
            "message": str(exception),
            "url": str(exception.request.url),
        }
    else:
        err = {
            "http_status": -1,
            "message": str(exception),
        }

    err["command_traceback"] = "".join(traceback.format_tb(exception.__traceback__))
    return err


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        None,
        callback=_load_config,
        help="Config file location. Defaults: \n" + ("\n").join(map(str, CONFIG_PATHS)),
        envvar="PMC_CLI_CONFIG",
    ),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for any background tasks."),
    no_color: bool = typer.Option(False, "--no-color", help="Suppress color output if enabled."),
    id_only: bool = typer.Option(False, "--id-only", help="Show ids instead of full responses."),
    resp_format: Format = typer.Option(Format.json, "--format", hidden=True),  # TODO: more formats
) -> None:
    if config and ctx.invoked_subcommand != "config":
        # validate config. allow users to still edit/recreate their config even if it's invalid.
        validate_config(config)

    ctx.obj = PMCContext(
        no_wait=no_wait,
        no_color=no_color,
        id_only=id_only,
        format=resp_format,
        config_path=config,
    )


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

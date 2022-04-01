import json
import sys
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable, List, Optional, Union

import httpx
import typer

from .client import client
from .commands import distribution, package, repository, task
from .schemas import Format

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

FINISHED_TASK_STATES = ("skipped", "completed", "failed", "canceled")

app = typer.Typer()
app.add_typer(distribution.app, name="distro")
app.add_typer(package.app, name="package")
app.add_typer(repository.app, name="repo")
app.add_typer(task.app, name="task")


@dataclass
class PMCContext:
    no_color: bool = False
    id_only: bool = False
    no_wait: bool = False
    format: str = "json"
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
        resp.raise_for_status()
        task = resp.json()

        if self.no_wait:
            return task

        typer.echo(f"Waiting for {task['id']}...", nl=False, err=True)

        while task["state"] not in FINISHED_TASK_STATES:
            sleep(1)
            resp = client.get(f"/tasks/{task['id']}/")
            resp.raise_for_status()
            task = resp.json()
            typer.echo(".", err=True, nl=False)

        typer.echo("", err=True)

        if task_handler:
            resp = task_handler(task)

        return resp

    def handle_response(self, resp: httpx.Response, task_handler: TaskHandler = None) -> None:
        resp.raise_for_status()

        if isinstance(resp.json(), dict) and (task_id := resp.json().get("task")):
            resp = self.poll_task(task_id, task_handler)
            resp.raise_for_status()

        if self.id_only and (id := self._extract_ids(resp.json())):
            typer.echo(id)
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


@app.callback()
def main(
    ctx: typer.Context,
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for any background tasks."),
    no_color: bool = typer.Option(False, "--no-color", help="Suppress color output if enabled."),
    id_only: bool = typer.Option(False, "--id-only", help="Show ids instead of full responses."),
    resp_format: Format = typer.Option(Format.json, "--format", hidden=True),  # TODO: more formats
) -> None:
    ctx.obj = PMCContext(no_wait=no_wait, no_color=no_color, id_only=id_only, format=resp_format)


if __name__ == "__main__":
    app()

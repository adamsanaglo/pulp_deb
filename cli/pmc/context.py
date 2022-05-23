import json
import sys
from pathlib import Path
from time import sleep
from typing import Any, Callable, List, Optional, Union

import httpx
import typer

from .client import get_client
from .schemas import FINISHED_TASK_STATES, Config

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


class PMCContext:
    def __init__(self, config: Config, config_path: Optional[Path] = None):
        self.config = config
        self.config_path = config_path
        self.isatty = sys.stdout.isatty()

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
        with get_client(self.config) as client:
            resp = client.get(f"/tasks/{task_id}/")
            task = resp.json()

            if self.config.no_wait:
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

        if self.config.id_only and (id := self._extract_ids(resp.json())):
            typer.echo(id, nl=self.isatty)
        else:
            if not self.isatty:
                # do not format output if it's not going to a terminal
                typer.echo(json.dumps(resp.json()))
            else:
                output = json.dumps(resp.json(), indent=3)
                if PYGMENTS and not self.config.no_color:
                    formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
                    output = highlight(output, JsonLexer(), formatter)
                typer.echo(output)

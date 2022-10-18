import json
from contextlib import contextmanager
from time import sleep
from typing import Any, Callable, Generator, List, Optional, Union

import httpx
import typer

from .context import PMCContext
from .schemas import FINISHED_TASK_STATES

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


def _log_request(request: httpx.Request) -> None:
    typer.echo(f"Request: {request.method} {request.url}")

    if "content-type" in request.headers and request.headers["content-type"] == "application/json":
        typer.echo(f"Body: {json.loads(request.content)}")


def _log_response(response: httpx.Response) -> None:
    request = response.request
    typer.echo(f"Response: {request.method} {request.url} - Status {response.status_code}")


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    response.raise_for_status()


@contextmanager
def get_client(ctx: PMCContext) -> Generator[httpx.Client, None, None]:
    request_hooks = []
    response_hooks = [_raise_for_status]

    if ctx.config.debug:
        request_hooks.append(_log_request)
        response_hooks.insert(0, _log_response)
    try:
        token = ctx.auth.acquire_token()
    except Exception:
        typer.echo("Failed to retrieve AAD token", err=True)
        raise
    client = httpx.Client(
        base_url=ctx.config.base_url,
        event_hooks={"request": request_hooks, "response": response_hooks},
        headers={"x-correlation-id": ctx.cid.hex, "Authorization": f"Bearer {token}"},
        timeout=None,
    )
    try:
        yield client
    finally:
        client.close()


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


def poll_task(ctx: PMCContext, task_id: str, task_handler: TaskHandler = None) -> Any:
    with get_client(ctx) as client:
        resp = client.get(f"/tasks/{task_id}/")
        task = resp.json()

        if ctx.config.no_wait:
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


def handle_response(
    ctx: PMCContext, resp: httpx.Response, task_handler: TaskHandler = None
) -> None:
    if not resp.content:
        # empty response
        return

    if isinstance(resp.json(), dict) and (task_id := resp.json().get("task")):
        resp = poll_task(ctx, task_id, task_handler)

    if ctx.config.id_only and (id := _extract_ids(resp.json())):
        typer.echo(id, nl=ctx.isatty)
    else:
        if not ctx.isatty:
            # do not format output if it's not going to a terminal
            typer.echo(json.dumps(resp.json()))
        else:
            output = json.dumps(resp.json(), indent=3)
            if PYGMENTS and not ctx.config.no_color:
                formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
                output = highlight(output, JsonLexer(), formatter)
            typer.echo(output)

import json
import shutil
from contextvars import ContextVar
from functools import partialmethod
from time import sleep
from typing import Any, Callable, List, Optional, Union

import click
import httpx
import typer

from .context import PMCContext
from .schemas import FINISHED_TASK_STATES

try:
    from pygments import highlight, styles
    from pygments.formatters import Terminal256Formatter
    from pygments.lexers import JsonLexer
except ImportError:
    PYGMENTS = False
else:
    PYGMENTS = True
    if "solarized-light" in styles.STYLE_MAP.keys():
        PYGMENTS_STYLE = "solarized-light"
    else:
        # old versions of pygments (< 2.4.0) don't have solarized
        PYGMENTS_STYLE = "native"


TaskHandler = Optional[Callable[[str], Any]]
client_context: ContextVar[httpx.Client] = ContextVar("client")


class ApiClient:
    """Wrapper class that will lazily pull the httpx client from the client contextvar.

    This allows the client variable to be imported from this module once without needing to call a
    function in each command function to fetch the client from the client_contextvar.
    """

    def request(self, *args: Any, **kwargs: Any) -> httpx.Response:
        client = client_context.get()
        resp = client.request(*args, **kwargs)
        return resp

    # define some methods that map to request
    get = partialmethod(request, "get")
    post = partialmethod(request, "post")
    patch = partialmethod(request, "patch")
    delete = partialmethod(request, "delete")


client = ApiClient()


def _set_auth_header(ctx: PMCContext, request: httpx.Request) -> None:
    try:
        token = ctx.auth.acquire_token()
    except Exception:
        typer.echo("Failed to retrieve AAD token", err=True)
        raise
    request.headers["Authorization"] = f"Bearer {token}"


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


def create_client(ctx: PMCContext) -> httpx.Client:
    def _call_set_auth_header(request: httpx.Request) -> None:
        _set_auth_header(ctx, request)

    request_hooks = [_call_set_auth_header]
    response_hooks = [_raise_for_status]

    if ctx.config.debug:
        request_hooks.append(_log_request)
        response_hooks.insert(0, _log_response)

    client = httpx.Client(
        base_url=ctx.config.base_url,
        event_hooks={"request": request_hooks, "response": response_hooks},
        headers={"x-correlation-id": ctx.cid.hex},
        timeout=None,
        verify=ctx.config.ssl_verify,
    )
    return client


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


def poll_task(task_id: str, task_handler: TaskHandler = None, quiet: bool = False) -> Any:
    resp = client.get(f"/tasks/{task_id}/")
    # While waiting for long tasks, we occasionally encounter an issue where our auth token
    # expires /right after/ we make a request and we get a 401. In that case let's simply try
    # again one extra time, which should trigger a re-auth and work.
    if resp.status_code == httpx.codes.UNAUTHORIZED:
        resp = client.get(f"/tasks/{task_id}/")

    task = resp.json()
    if not quiet:
        typer.echo(f"Waiting for {task['id']}...", nl=False, err=True)

    while task["state"] not in FINISHED_TASK_STATES:
        sleep(1)
        resp = client.get(f"/tasks/{task['id']}/")
        task = resp.json()
        if not quiet:
            typer.echo(".", err=True, nl=False)

    if not quiet:
        typer.echo("", err=True)

    if task_handler:
        resp = task_handler(task)
    else:
        if not quiet:
            typer.echo("Done.", err=True)

    return resp


def output_json(ctx: PMCContext, output: Any, suppress_pager: bool = False) -> None:
    if ctx.config.id_only and (id := _extract_ids(output)):
        typer.echo(id, nl=ctx.isatty)
    else:
        json_output = json.dumps(output, indent=3)

        if PYGMENTS and not ctx.config.no_color:
            formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
            json_output = highlight(json_output, JsonLexer(), formatter)

        if (
            ctx.config.pager
            and not suppress_pager
            and json_output.count("\n") > shutil.get_terminal_size().lines - 3
        ):
            click.echo_via_pager(json_output)
        else:
            typer.echo(json_output)


def handle_response(
    ctx: PMCContext, resp: httpx.Response, task_handler: TaskHandler = None
) -> None:
    if not resp.content:
        # empty response
        return

    if isinstance(resp.json(), dict):
        task_id = resp.json().get("task")
    else:
        task_id = None

    if not ctx.config.no_wait and task_id:
        resp = poll_task(task_id, task_handler, ctx.config.quiet)

    output_json(ctx, resp.json(), task_id is not None)

import json
import shutil
from contextvars import ContextVar
from functools import partialmethod
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Union

import click
import requests
import typer
from requests.auth import AuthBase

from .constants import CLI_VERSION, LIST_SEPARATOR
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


TaskHandler = Optional[Callable[[str], requests.Response]]


class ApiClient:
    """Wrapper class that will lazily pull the requests session from the session contextvar.

    This allows the session variable to be imported from this module once without needing to call a
    function in each command function to fetch the session from the session_contextvar.
    """

    def request(self, *args: Any, **kwargs: Any) -> requests.Response:
        session = session_context.get()
        return session.request(*args, **kwargs)

    # define some methods that map to request
    get = partialmethod(request, "get")
    post = partialmethod(request, "post")
    patch = partialmethod(request, "patch")
    delete = partialmethod(request, "delete")


client = ApiClient()


class TokenAuth(AuthBase):
    def __init__(self, token: str) -> None:
        self.token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers["authorization"] = f"Bearer {self.token}"
        return r


class ClientSession(requests.Session):
    def __init__(self, ctx: PMCContext):
        super().__init__()
        self.context = ctx
        self.verify = self.context.ssl_verify

    def _get_headers(self) -> Dict[str, Any]:
        """
        Auto-increment our correlation id for every request we make with this context.
        This allows us to more easily trace through the server logs for a given request, but we can
        still find related before-or-after requests if we need to.

        The Auth token is pretty self-explanatory.
        """
        headers = {}

        # increment and set correlation id
        i = int(self.context.cid, 16)
        self.context.cid = format(i + 1, "x")
        headers["x-correlation-id"] = self.context.cid

        headers["pmc-cli-version"] = CLI_VERSION

        return headers

    def request(
        self, method: Union[str, bytes], url: Union[str, bytes], *args: Any, **kwargs: Any
    ) -> requests.Response:
        url = f"{self.context.base_url}{str(url)}"

        if "headers" not in kwargs:
            kwargs["headers"] = self._get_headers()

        if "timeout" not in kwargs:
            kwargs["timeout"] = 600

        if self.context.debug:
            typer.echo(f"Request: {str(method)} {str(url)}")

        try:
            token = self.context.auth.acquire_token()
        except Exception:
            typer.echo("Failed to retrieve AAD token", err=True)
            raise
        kwargs["auth"] = TokenAuth(token)

        response = super().request(method, url, *args, **kwargs)

        if self.context.debug:
            typer.echo(f"Response: {str(method)} {str(url)} - Status {response.status_code}")

        response.raise_for_status()

        return response


session_context: ContextVar[ClientSession] = ContextVar("client")


def init_session(ctx: PMCContext) -> ClientSession:
    session = ClientSession(ctx)
    session_context.set(session)
    return session


def _extract_ids(resp_json: Any) -> Union[str, List[str], None]:
    if isinstance(resp_json, dict):
        if id := resp_json.get("id"):
            return [str(id)]
        elif task_id := resp_json.get("task"):
            return [str(task_id)]
        elif results := resp_json.get("results"):
            return [r["id"] for r in results]
    elif isinstance(resp_json, list):
        if len(resp_json) > 0 and resp_json[0].get("id"):
            return [r["id"] for r in resp_json]

    return None


def poll_task(
    task_id: str, task_handler: TaskHandler = None, quiet: bool = False
) -> requests.Response:
    resp = client.get(f"/tasks/{task_id}/")
    # While waiting for long tasks, we occasionally encounter an issue where our auth token
    # expires /right after/ we make a request and we get a 401. In that case let's simply try
    # again one extra time, which should trigger a re-auth and work.
    if resp.status_code == requests.codes.UNAUTHORIZED:
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
    if ctx.id_only and (ids := _extract_ids(output)):
        typer.echo((LIST_SEPARATOR).join(ids), nl=ctx.isatty)
    else:
        json_output = json.dumps(output, indent=3)

        if PYGMENTS and not ctx.no_color:
            formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
            json_output = highlight(json_output, JsonLexer(), formatter)

        if (
            ctx.pager
            and not suppress_pager
            and json_output.count("\n") > shutil.get_terminal_size().lines - 3
        ):
            click.echo_via_pager(json_output)
        else:
            typer.echo(json_output)


def handle_response(
    ctx: PMCContext, resp: requests.Response, task_handler: TaskHandler = None
) -> None:
    if not resp.content:
        # empty response
        return

    if isinstance(resp.json(), dict):
        task_id = resp.json().get("task")
    else:
        task_id = None

    if not ctx.no_wait and task_id:
        resp = poll_task(task_id, task_handler, ctx.quiet)

    output = resp.json()
    output_json(ctx, output, task_id is not None)
    if (
        isinstance(output, Dict)
        and output.get("count", 0) > len(output.get("results", []))
        and output.get("offset", -1) == 0
        and not ctx.quiet
    ):
        typer.echo(
            "Warning: Results are paginated. Use --offset (and/or --limit) to view more results.",
            err=True,
        )

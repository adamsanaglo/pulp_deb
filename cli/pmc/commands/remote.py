from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import get_client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, RemoteType

app = typer.Typer()

repo_option = typer.Option(None, help="Repository to distribute.")


@app.command()
def list(
    ctx: typer.Context, limit: Optional[int] = LIMIT_OPT, offset: Optional[int] = OFFSET_OPT
) -> None:
    """List remotes."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get("/remotes/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
def create(
    ctx: typer.Context,
    name: str,
    remote_type: RemoteType,
    url: str,
    distributions: Optional[str] = typer.Option(
        None, help="Semicolon-separated list of releases/dists."
    ),
    components: Optional[str] = typer.Option(None, help="Semicolon separated list of comps."),
    architectures: Optional[str] = typer.Option(
        None, help="Semicolon-separated list of architectures."
    ),
) -> None:
    """Create a remote."""

    def show_func(task: Any) -> httpx.Response:
        assert isinstance(task, Dict) and task.get("created_resources")
        new_id = task["created_resources"][0]
        with get_client(ctx.obj) as client:
            return client.get(f"/remotes/{new_id}/")

    data: Dict[str, Any] = {
        "name": name,
        "type": remote_type,
        "url": url,
    }
    if distributions:
        data["distributions"] = distributions.split(LIST_SEPARATOR)
    if components:
        data["components"] = components.split(LIST_SEPARATOR)
    if architectures:
        data["architectures"] = architectures.split(LIST_SEPARATOR)

    with get_client(ctx.obj) as client:
        resp = client.post("/remotes/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a remote."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/remotes/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def update(
    ctx: typer.Context,
    id: str,
    name: Optional[str] = typer.Option(None),
    url: Optional[str] = typer.Option(None),
    distributions: Optional[str] = typer.Option(
        None, help="Whitespace separated list of releases/dists."
    ),
    components: Optional[str] = typer.Option(None, help="Whitespace separated list of comps."),
    architectures: Optional[str] = typer.Option(
        None, help="Whitespace separated list of architectures."
    ),
) -> None:
    """Update a remote."""

    def show_func(task: Any) -> httpx.Response:
        with get_client(ctx.obj) as client:
            return client.get(f"/remotes/{id}/")

    data = {}
    if name:
        data["name"] = name
    if url:
        data["url"] = url
    if distributions:
        data["distributions"] = distributions
    if components:
        data["components"] = components
    if architectures:
        data["architectures"] = architectures

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/remotes/{id}/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a remote."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/remotes/{id}/")
        handle_response(ctx.obj, resp)

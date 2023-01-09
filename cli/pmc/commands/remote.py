from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, RemoteType
from pmc.utils import UserFriendlyTyper, id_or_name

app = UserFriendlyTyper()

DISTRIBUTIONS_HELP = "Semicolon-separated list of releases/dists."
COMPONENTS_HELP = "Semicolon separated list of comps."
ARCHITECTURES_HELP = "Semicolon-separated list of architectures."


@app.command()
def list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List remotes."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    resp = client.get("/remotes/", params=params)
    handle_response(ctx.obj, resp)


@app.restricted_command()
def create(
    ctx: typer.Context,
    name: str,
    remote_type: RemoteType,
    url: str,
    distributions: Optional[str] = typer.Option(None, help=DISTRIBUTIONS_HELP),
    components: Optional[str] = typer.Option(None, help=COMPONENTS_HELP),
    architectures: Optional[str] = typer.Option(None, help=ARCHITECTURES_HELP),
) -> None:
    """Create a remote."""

    def show_func(task: Any) -> httpx.Response:
        assert isinstance(task, Dict) and task.get("created_resources")
        new_id = task["created_resources"][0]
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

    resp = client.post("/remotes/", json=data)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("remotes")) -> None:
    """Show details for a remote."""
    resp = client.get(f"/remotes/{id}/")
    handle_response(ctx.obj, resp)


@app.restricted_command()
def update(
    ctx: typer.Context,
    id: str = id_or_name("remotes"),
    name: Optional[str] = typer.Option(None),
    url: Optional[str] = typer.Option(None),
    distributions: Optional[str] = typer.Option(None, help=DISTRIBUTIONS_HELP),
    components: Optional[str] = typer.Option(None, help=COMPONENTS_HELP),
    architectures: Optional[str] = typer.Option(None, help=ARCHITECTURES_HELP),
) -> None:
    """Update a remote."""

    def show_func(task: Any) -> httpx.Response:
        return client.get(f"/remotes/{id}/")

    data: Dict[str, Any] = {}
    if name:
        data["name"] = name
    if url:
        data["url"] = url
    if distributions:
        data["distributions"] = distributions.split(LIST_SEPARATOR)
    if components:
        data["components"] = components.split(LIST_SEPARATOR)
    if architectures:
        data["architectures"] = architectures.split(LIST_SEPARATOR)

    resp = client.patch(f"/remotes/{id}/", json=data)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.restricted_command()
def delete(ctx: typer.Context, id: str = id_or_name("remotes")) -> None:
    """Delete a remote."""
    resp = client.delete(f"/remotes/{id}/")
    handle_response(ctx.obj, resp)

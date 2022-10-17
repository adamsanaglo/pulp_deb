from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, DistroType
from pmc.utils import UserFriendlyTyper, id_or_name

app = UserFriendlyTyper()

repo_option = id_or_name(
    "repositories",
    typer.Option(None, "--repository", "--repo", help="Repository id or name to distribute."),
)


@app.command()
def list(
    ctx: typer.Context,
    base_path: str = typer.Option(None, help="Filter by base_path"),
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
) -> None:
    """List distributions."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    if base_path:
        params["base_path"] = base_path

    with get_client(ctx.obj) as client:
        resp = client.get("/distributions/", params=params)
        handle_response(ctx.obj, resp)


@app.restricted_command()
def create(
    ctx: typer.Context,
    name: str,
    distro_type: DistroType,
    base_path: str,
    repository: Optional[str] = repo_option,
) -> None:
    """Create a distribution."""

    def show_func(task: Any) -> httpx.Response:
        assert isinstance(task, Dict) and task.get("created_resources")
        new_id = task["created_resources"][0]
        with get_client(ctx.obj) as client:
            return client.get(f"/distributions/{new_id}/")

    data = {
        "name": name,
        "type": distro_type,
        "base_path": base_path,
    }

    if repository:
        data["repository"] = repository

    with get_client(ctx.obj) as client:
        resp = client.post("/distributions/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("distributions")) -> None:
    """Show details for a distribution."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/distributions/{id}/")
        handle_response(ctx.obj, resp)


@app.restricted_command()
def update(
    ctx: typer.Context,
    id: str = id_or_name("distributions"),
    name: Optional[str] = typer.Option(None),
    base_path: Optional[str] = typer.Option(None),
    repository: Optional[str] = repo_option,
) -> None:
    """Update a distribution."""

    def show_func(task: Any) -> httpx.Response:
        with get_client(ctx.obj) as client:
            return client.get(f"/distributions/{id}/")

    data = {}
    if name:
        data["name"] = name
    if base_path:
        data["base_path"] = base_path
    if repository:
        data["repository"] = repository

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/distributions/{id}/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.restricted_command()
def delete(ctx: typer.Context, id: str = id_or_name("distributions")) -> None:
    """Delete a distribution."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/distributions/{id}/")
        handle_response(ctx.obj, resp)

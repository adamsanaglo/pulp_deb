from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, DistroType
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

app = UserFriendlyTyper()

repo_option = id_or_name(
    "repositories",
    typer.Option(None, "--repository", "--repo", help="Repository id or name to distribute."),
)


@app.command()
def list(
    ctx: typer.Context,
    name: str = typer.Option(None, help="Filter by name"),
    name_contains: str = typer.Option(None, help="Filter distros whose names contain string"),
    base_path: str = typer.Option(None, help="Filter by base_path"),
    base_path_contains: str = typer.Option(
        None, help="Filter distros whose base path contain string"
    ),
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List distributions."""
    params = build_params(
        limit,
        offset,
        name=name,
        name__contains=name_contains,
        base_path=base_path,
        base_path__contains=base_path_contains,
    )

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
        return client.get(f"/distributions/{new_id}/")

    data = {
        "name": name,
        "type": distro_type,
        "base_path": base_path,
    }

    if repository:
        data["repository"] = repository

    resp = client.post("/distributions/", json=data)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("distributions")) -> None:
    """Show details for a distribution."""
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
        return client.get(f"/distributions/{id}/")

    data = {}
    if name:
        data["name"] = name
    if base_path:
        data["base_path"] = base_path
    if repository:
        data["repository"] = repository

    resp = client.patch(f"/distributions/{id}/", json=data)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.restricted_command()
def delete(ctx: typer.Context, id: str = id_or_name("distributions")) -> None:
    """Delete a distribution."""
    resp = client.delete(f"/distributions/{id}/")
    handle_response(ctx.obj, resp)

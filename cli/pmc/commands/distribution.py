from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, DistroType

app = typer.Typer()

repo_option = typer.Option(None, help="Repository to distribute.")


@app.command()
def list(
    ctx: typer.Context, limit: Optional[int] = LIMIT_OPT, offset: Optional[int] = OFFSET_OPT
) -> None:
    """List distributions."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get("/distributions/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
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
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a distribution."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/distributions/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def update(
    ctx: typer.Context,
    id: str,
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


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a distribution."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/distributions/{id}/")
        handle_response(ctx.obj, resp)

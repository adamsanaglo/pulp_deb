from typing import Any, Dict, Optional

import httpx
import typer

from pmc.client import client
from pmc.schemas import DistroType

app = typer.Typer()


@app.command()
def list(ctx: typer.Context) -> None:
    """List distributions."""
    resp = client.get("/distributions/")
    ctx.obj.handle_response(resp)


@app.command()
def create(
    ctx: typer.Context,
    name: str,
    distro_type: DistroType,
    base_path: str,
    repository: Optional[str] = typer.Option(None),
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
    ctx.obj.handle_response(resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a distribution."""
    resp = client.get(f"/distributions/{id}/")
    ctx.obj.handle_response(resp)


@app.command()
def update(
    ctx: typer.Context,
    id: str,
    name: Optional[str] = typer.Option(None),
    base_path: Optional[str] = typer.Option(None),
    repository_id: Optional[str] = typer.Option(None),
) -> None:
    """Update a distribution."""

    def show_func(task: Any) -> httpx.Response:
        return client.get(f"/distributions/{id}/")

    data = {}
    if name:
        data["name"] = name
    if base_path:
        data["base_path"] = base_path
    if repository_id:
        data["repository"] = repository_id

    resp = client.patch(f"/distributions/{id}/", json=data)
    ctx.obj.handle_response(resp, task_handler=show_func)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a distribution."""
    resp = client.delete(f"/distributions/{id}/")
    ctx.obj.handle_response(resp)

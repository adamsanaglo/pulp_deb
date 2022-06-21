from typing import Any, Dict, Optional

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, RepoType

app = typer.Typer()
packages = typer.Typer()
app.add_typer(packages, name="packages")


@app.command()
def list(
    ctx: typer.Context,
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
    name: Optional[str] = typer.Option(None),
) -> None:
    """List repositories."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)
    if name:
        params["name"] = name

    with get_client(ctx.obj) as client:
        resp = client.get("/repositories/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
def create(ctx: typer.Context, name: str, repo_type: RepoType) -> None:
    """Create a repository."""
    data = {"name": name, "type": repo_type}
    with get_client(ctx.obj) as client:
        resp = client.post("/repositories/", json=data)
        handle_response(ctx.obj, resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular repository."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/repositories/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def update(ctx: typer.Context, id: str, name: str = typer.Option("")) -> None:
    """Update a repository."""

    def show_func(task: Any) -> Any:
        with get_client(ctx.obj) as client:
            return client.get(f"/repositories/{id}/")

    data = {}
    if name:
        data["name"] = name

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/repositories/{id}/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a repository."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/repositories/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def publish(ctx: typer.Context, id: str) -> None:
    """Publish a repository making its packages available and updating its metadata."""
    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{id}/publish/")
        handle_response(ctx.obj, resp)


@packages.command(name="list")
def list_packages(ctx: typer.Context, repo_id: str) -> None:
    """List packages for a repository."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/repositories/{repo_id}/packages/")
        handle_response(ctx.obj, resp)


@packages.command(name="update")
def update_packages(
    ctx: typer.Context,
    repo_id: str,
    add_packages: Optional[str] = typer.Option(None),
    remove_packages: Optional[str] = typer.Option(None),
) -> None:
    """Add or remove packages from a repository."""
    data = {}
    if add_packages:
        data["add_packages"] = add_packages.split(",")
    if remove_packages:
        data["remove_packages"] = remove_packages.split(",")

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/repositories/{repo_id}/packages/", json=data)
        handle_response(ctx.obj, resp)

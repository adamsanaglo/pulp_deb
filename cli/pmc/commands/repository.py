from typing import Any, Optional

import typer

from pmc.client import client
from pmc.schemas import RepoType

app = typer.Typer()
packages = typer.Typer()
app.add_typer(packages, name="packages")


@app.command()
def list(ctx: typer.Context, name: Optional[str] = typer.Option(None)) -> None:
    """List repositories."""
    params = {}
    if name:
        params["name"] = name
    resp = client.get("/repositories/", params=params)
    ctx.obj.handle_response(resp)


@app.command()
def create(ctx: typer.Context, name: str, repo_type: RepoType) -> None:
    """Create a repository."""
    data = {"name": name, "type": repo_type}
    resp = client.post("/repositories/", json=data)
    ctx.obj.handle_response(resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular repository."""
    resp = client.get(f"/repositories/{id}/")
    ctx.obj.handle_response(resp)


@app.command()
def update(ctx: typer.Context, id: str, name: str = typer.Option("")) -> None:
    """Update a repository."""

    def show_func(task: Any) -> Any:
        return client.get(f"/repositories/{id}/")

    data = {}
    if name:
        data["name"] = name
    resp = client.patch(f"/repositories/{id}/", json=data)
    ctx.obj.handle_response(resp, task_handler=show_func)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a repository."""
    resp = client.delete(f"/repositories/{id}/")
    ctx.obj.handle_response(resp)


@app.command()
def publish(ctx: typer.Context, id: str) -> None:
    """Publish a repository making its packages available and updating its metadata."""
    resp = client.post(f"/repositories/{id}/publish/")
    ctx.obj.handle_response(resp)


@packages.command(name="list")
def list_packages(ctx: typer.Context, repo_id: str) -> None:
    """List packages for a repository."""
    resp = client.get(f"/repositories/{repo_id}/packages/")
    ctx.obj.handle_response(resp)


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
    resp = client.patch(f"/repositories/{repo_id}/packages/", json=data)
    ctx.obj.handle_response(resp)

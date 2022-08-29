from typing import Any, Dict, List, Optional, Union

import typer

from pmc.client import get_client, handle_response
from pmc.commands.release import releases
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, RepoType

app = typer.Typer()
packages = typer.Typer(help="Manage a repo's packages.")
app.add_typer(packages, name="packages")
app.add_typer(releases, name="releases")

ADD_PACKAGES_HELP = "Semicolon-separated list of package ids to add."
REMOVE_PACKAGES_HELP = "Semicolon-separated list of package ids to remove."


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
def create(
    ctx: typer.Context,
    name: str,
    repo_type: RepoType,
    remote: Optional[str] = typer.Option(None, help="Remote id to use for sync."),
) -> None:
    """Create a repository."""
    data = {"name": name, "type": repo_type, "remote": remote}
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
def update(
    ctx: typer.Context,
    id: str,
    name: str = typer.Option(""),
    remote: Optional[str] = typer.Option(None, help="Remote id to use for sync"),
) -> None:
    """Update a repository."""

    def show_func(task: Any) -> Any:
        with get_client(ctx.obj) as client:
            return client.get(f"/repositories/{id}/")

    data: Dict[str, Any] = {}
    if name:
        data["name"] = name
    if remote is not None:
        if remote == "":
            data["remote"] = None  # unset remote
        else:
            data["remote"] = remote

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
def sync(
    ctx: typer.Context,
    id: str,
    remote: Optional[str] = typer.Option(None, help="Optional remote id to use for sync."),
) -> None:
    """Sync a repository."""
    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{id}/sync/")
        handle_response(ctx.obj, resp)


@app.command()
def publish(ctx: typer.Context, id: str) -> None:
    """Publish a repository making its packages available and updating its metadata."""
    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{id}/publish/")
        handle_response(ctx.obj, resp)


@packages.command(name="list")
def list_packages(
    ctx: typer.Context,
    repo_id: str,
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
) -> None:
    """List packages for a repository."""
    params = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get(f"/repositories/{repo_id}/packages/", params=params)
        handle_response(ctx.obj, resp)


@packages.command(name="update")
def update_packages(
    ctx: typer.Context,
    repo_id: str,
    release: str = typer.Argument(None, help="Release/dist to add packages to."),
    component: str = typer.Argument(None, help="Component to add packages to."),
    add_packages: Optional[str] = typer.Option(None, help=ADD_PACKAGES_HELP),
    remove_packages: Optional[str] = typer.Option(None, help=REMOVE_PACKAGES_HELP),
) -> None:
    """Add or remove packages from a repository."""
    data: Dict[str, Union[str, List[str]]] = {}
    if add_packages:
        data["add_packages"] = add_packages.split(LIST_SEPARATOR)
    if remove_packages:
        data["remove_packages"] = remove_packages.split(LIST_SEPARATOR)
    if release:
        data["release"] = release
    if component:
        data["component"] = component

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/repositories/{repo_id}/packages/", json=data)
        handle_response(ctx.obj, resp)

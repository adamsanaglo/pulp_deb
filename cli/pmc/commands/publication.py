from typing import Optional

import typer

from pmc.client import client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

app = UserFriendlyTyper()


repo_option = id_or_name(
    "repositories",
    typer.Option(None, "--repository", "--repo", help="Filter publications by a repo name or id."),
)


@app.command()
def list(
    ctx: typer.Context,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    repo_id: str = repo_option,
    package: str = typer.Option(None, help="Filter publication that contain a package with id."),
) -> None:
    """List publications."""
    params = build_params(limit, offset, repository=repo_id, package=package)
    resp = client.get("/publications/", params=params)
    handle_response(ctx.obj, resp)


@app.command()
def show(
    ctx: typer.Context,
    id: Optional[str] = typer.Argument(None, help="Publication id."),
) -> None:
    """Show a publication by id."""
    resp = client.get(f"/publications/{id}/")
    handle_response(ctx.obj, resp)


@app.command()
def delete(
    ctx: typer.Context,
    id: Optional[str] = typer.Argument(None, help="Publication id."),
) -> None:
    """Delete a publication by id."""
    resp = client.delete(f"/publications/{id}/")
    handle_response(ctx.obj, resp)

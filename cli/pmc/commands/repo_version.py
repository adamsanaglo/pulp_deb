from typing import Optional

import typer
from click import BadParameter

from pmc.client import client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

version = UserFriendlyTyper(help="Manage repository versions.")


repo_option = id_or_name(
    "repositories",
    typer.Option(None, "--repository", "--repo", help="Filter repo versions by a repo name or id."),
)


@version.command()
def list(
    ctx: typer.Context,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    repo_id: str = repo_option,
    number: int = typer.Option(None, help="Filter versions by number."),
    package: str = typer.Option(None, help="Filter versions that contain a package with id."),
) -> None:
    """List repository versions."""
    params = build_params(limit, offset, repository=repo_id, number=number, package=package)
    resp = client.get("/repository_versions/", params=params)
    handle_response(ctx.obj, resp)


@version.command()
def show(
    ctx: typer.Context,
    id: Optional[str] = typer.Argument(None, help="Repo verison id."),
    repo_id: str = repo_option,
    number: int = typer.Option(None, help="Version number."),
) -> None:
    """Show a repo version by id or with repo id and number."""
    if not id:
        if not repo_id or number:
            raise BadParameter("Must supply id or repo id and number.")
        else:
            id = f"{repo_id}-versions-{number}"

    resp = client.get(f"/repository_versions/{id}/")
    handle_response(ctx.obj, resp)


@version.command()
def delete(
    ctx: typer.Context,
    id: Optional[str] = typer.Argument(None, help="Repo verison id."),
    repo_id: str = repo_option,
    number: int = typer.Option(None, help="Version number."),
) -> None:
    """Delete a repo version by id or with repo id and number."""
    if not id:
        if not repo_id or number:
            raise BadParameter("Must supply id or repo id and number.")
        else:
            id = f"{repo_id}-versions-{number}"

    resp = client.delete(f"/repository_versions/{id}/")
    handle_response(ctx.obj, resp)

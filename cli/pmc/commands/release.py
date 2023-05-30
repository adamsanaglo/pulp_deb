from typing import Dict, List, Optional, Union

import typer

from pmc.client import client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

releases = UserFriendlyTyper(help="Manage a repo's releases.")

repo_option = id_or_name(
    "repositories", typer.Argument(..., help="Repository id or name for which to manage releases.")
)


@releases.command()
def list(
    ctx: typer.Context,
    repo_id: str = repo_option,
    name: Optional[str] = typer.Argument(None, help="Name of the release we're looking for."),
    package: Optional[str] = typer.Option(
        None, help="PackageId, only list releases that contain this package."
    ),
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List a repository's releases."""
    params = build_params(limit, offset, name=name, package=package)

    resp = client.get(f"/repositories/{repo_id}/releases/", params=params)
    handle_response(ctx.obj, resp)


@releases.restricted_command()
def create(
    ctx: typer.Context,
    repo_id: str = repo_option,
    name: str = typer.Argument(..., help="Name under which to distribute release."),
    codename: Optional[str] = typer.Argument(None, help="Codename for the release."),
    suite: Optional[str] = typer.Argument(None, help="Suite for the release (e.g. stable)."),
    components: str = typer.Option(
        None, help=f"{LIST_SEPARATOR.title}-separated list of components."
    ),
    architectures: str = typer.Option(
        None, help=f"{LIST_SEPARATOR.title}-separated list of architectures."
    ),
) -> None:
    """Create a release for a repository."""
    data: Dict[str, Union[str, List[str]]] = {"name": name}
    if codename:
        data["codename"] = codename
    if suite:
        data["suite"] = suite

    if components:
        data["components"] = components.split(LIST_SEPARATOR)
    if architectures:
        data["architectures"] = architectures.split(LIST_SEPARATOR)

    resp = client.post(f"/repositories/{repo_id}/releases/", json=data)
    handle_response(ctx.obj, resp)


@releases.restricted_command()
def update(
    ctx: typer.Context,
    repository: str = repo_option,
    id: str = id_or_name(
        "repositories/%(repository)s/releases", typer.Argument(..., help="The release name or id.")
    ),
    add_architectures: str = typer.Option(
        None, help=f"{LIST_SEPARATOR.title}-separated list of architectures to add to the release."
    ),
) -> None:
    data = {}
    if add_architectures:
        data["add_architectures"] = add_architectures.split(LIST_SEPARATOR)

    resp = client.patch(f"/repositories/{repository}/releases/{id}/", json=data)
    handle_response(ctx.obj, resp)


@releases.restricted_command()
def delete(
    ctx: typer.Context,
    repository: str = repo_option,
    id: str = id_or_name("repositories/%(repository)s/releases"),
) -> None:
    """Delete a repository release."""
    resp = client.delete(f"/repositories/{repository}/releases/{id}/")
    handle_response(ctx.obj, resp)

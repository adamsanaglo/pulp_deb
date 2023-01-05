from typing import Any, Dict, List, Optional, Union

import typer

from pmc.client import client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import UserFriendlyTyper, id_or_name

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
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
) -> None:
    """List a repository's releases."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)
    if name:
        params["name"] = name
    if package:
        params["package"] = package

    resp = client.get(f"/repositories/{repo_id}/releases/", params=params)
    handle_response(ctx.obj, resp)


@releases.restricted_command()
def create(
    ctx: typer.Context,
    repo_id: str = repo_option,
    name: str = typer.Argument(..., help="Name under which to distribute release."),
    codename: Optional[str] = typer.Argument(None, help="Codename for the release."),
    suite: Optional[str] = typer.Argument(None, help="Suite for the release (e.g. stable)."),
    components: str = typer.Option(None, help="Semicolon-separated list of components."),
    architectures: str = typer.Option(None, help="Semicolon-separated list of architectures."),
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

from typing import Dict, List, Optional, Union

import typer

from pmc.client import get_client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import id_or_name

app = typer.Typer()
releases = typer.Typer(help="Manage a repo's releases.")

repo_option = id_or_name(
    "repositories", typer.Argument(..., help="Repository id or name for which to manage releases.")
)


@releases.command()
def list(
    ctx: typer.Context,
    repo_id: str = repo_option,
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
) -> None:
    """List a repository's releases."""
    params = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get(f"/repositories/{repo_id}/releases/", params=params)
        handle_response(ctx.obj, resp)


@releases.command()
def create(
    ctx: typer.Context,
    repo_id: str = repo_option,
    distribution: str = typer.Argument(..., help="Name under which to distribute release."),
    codename: str = typer.Argument(..., help="Codename for the release."),
    suite: str = typer.Argument(..., help="Suite for the release (e.g. stable)."),
    components: str = typer.Option(None, help="Semicolon-separated list of components."),
    architectures: str = typer.Option(None, help="Semicolon-separated list of architectures."),
) -> None:
    """Create a release for a repository."""
    data: Dict[str, Union[str, List[str]]] = {
        "codename": codename,
        "suite": suite,
        "distribution": distribution,
    }

    if components:
        data["components"] = components.split(LIST_SEPARATOR)
    if architectures:
        data["architectures"] = architectures.split(LIST_SEPARATOR)

    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{repo_id}/releases/", json=data)
        handle_response(ctx.obj, resp)

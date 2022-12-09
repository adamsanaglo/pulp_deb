from typing import Any, Dict, List, Optional, Union

import typer

from pmc.client import get_client, handle_response, poll_task
from pmc.commands.release import releases
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, RepoSigningService, RepoType
from pmc.utils import UserFriendlyTyper, id_or_name

app = UserFriendlyTyper()
packages = UserFriendlyTyper(help="Manage a repo's packages.")
app.add_typer(packages, name="package")
app.add_typer(releases, name="release")

ADD_PACKAGES_HELP = "Semicolon-separated list of package ids to add."
REMOVE_PACKAGES_HELP = "Semicolon-separated list of package ids to remove."
RELEASE_HELP = (
    "Name of the apt release whose packages you're managing. "
    "Release is required if you're adding packages to an apt repo, or removing packages from a "
    "specific apt release only. "
    "You can also remove the packages from ALL releases in an apt repo by not specifying it in "
    "a remove operation. "
    "This option does nothing for yum repos."
)

sqlite_metadata_option = typer.Option(
    None, help="Enable the generation of sqlite metadata files for yum repos (Deprecated)."
)


@app.command()
def list(
    ctx: typer.Context,
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
    name: Optional[str] = typer.Option(None),
    name_contains: Optional[str] = typer.Option(
        None, help="Filter repos with names that contain string."
    ),
    name_icontains: Optional[str] = typer.Option(
        None, help="Filter repos with names that contain string (case insensitive)."
    ),
) -> None:
    """List repositories."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)
    if name:
        params["name"] = name
    if name_contains:
        params["name__contains"] = name_contains
    if name_icontains:
        params["name__icontains"] = name_icontains

    with get_client(ctx.obj) as client:
        resp = client.get("/repositories/", params=params)
        handle_response(ctx.obj, resp)


@app.restricted_command()
def create(
    ctx: typer.Context,
    name: str,
    repo_type: RepoType,
    signing_service: Optional[RepoSigningService] = typer.Option(
        None,
        help="Signing service to use for the repo. Defaults to 'esrp' for yum and apt repos.",
    ),
    remote: Optional[str] = id_or_name(
        "remotes", typer.Option(None, help="Remote id or name to use for sync.")
    ),
    releases: Optional[str] = typer.Option(
        None, help=f"Create releases with names separated by {LIST_SEPARATOR}"
    ),
    paths: Optional[str] = typer.Option(
        None, help=f"Create distributions with paths separated by {LIST_SEPARATOR}"
    ),
    sqlite_metadata: Optional[bool] = sqlite_metadata_option,
) -> None:
    """Create a repository."""
    data: Dict[str, Any] = {"name": name, "type": repo_type, "remote": remote}

    if releases and repo_type != RepoType.apt:
        raise Exception(f"Cannot create releases for {repo_type} repos.")

    if sqlite_metadata:
        typer.echo("Warning: sqlite_metadata is deprecated.", err=True)
        data["sqlite_metadata"] = sqlite_metadata

    # set signing service
    if repo_type in [RepoType.yum, RepoType.apt]:
        if signing_service:
            service = signing_service
        elif service_default := (ctx.find_root().default_map or {}).get("signing_service"):
            service = service_default
        else:
            service = RepoSigningService.esrp

        data["signing_service"] = service

    with get_client(ctx.obj) as client:
        repo_resp = client.post("/repositories/", json=data)
        handle_response(ctx.obj, repo_resp)
        repo_id = repo_resp.json()["id"]

        if releases:
            for release in releases.split(LIST_SEPARATOR):
                typer.echo(f"Creating release '{release}'.", err=True)
                resp = client.post(f"/repositories/{repo_id}/releases/", json={"name": release})
                poll_task(ctx.obj, resp.json().get("task"))

        if paths:
            for path in paths.split(LIST_SEPARATOR):
                typer.echo(f"Creating distribution '{path}'.", err=True)
                distro = {
                    "repository": repo_id,
                    "type": repo_type,
                    "name": path,
                    "base_path": path,
                }
                resp = client.post("/distributions/", json=distro)
                poll_task(ctx.obj, resp.json().get("task"))


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("repositories")) -> None:
    """Show details for a particular repository."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/repositories/{id}/")
        handle_response(ctx.obj, resp)


@app.restricted_command()
def update(
    ctx: typer.Context,
    id: str = id_or_name("repositories"),
    name: str = typer.Option(""),
    signing_service: RepoSigningService = typer.Option(None, help="What signing service to use."),
    remote: Optional[str] = id_or_name(
        "remotes", typer.Option(None, help="Remote id or name to use for sync.")
    ),
    sqlite_metadata: Optional[bool] = sqlite_metadata_option,
) -> None:
    """Update a repository."""

    def show_func(task: Any) -> Any:
        with get_client(ctx.obj) as client:
            return client.get(f"/repositories/{id}/")

    data: Dict[str, Any] = {}
    if name:
        data["name"] = name
    if signing_service:
        data["signing_service"] = signing_service
    if remote is not None:
        if remote == "":
            data["remote"] = None  # unset remote
        else:
            data["remote"] = remote
    if sqlite_metadata is not None:
        if sqlite_metadata:
            typer.echo("Warning: sqlite_metadata is deprecated.", err=True)
        data["sqlite_metadata"] = sqlite_metadata

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/repositories/{id}/", json=data)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.restricted_command()
def delete(ctx: typer.Context, id: str = id_or_name("repositories")) -> None:
    """Delete a repository."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/repositories/{id}/")
        handle_response(ctx.obj, resp)


@app.restricted_command()
def sync(
    ctx: typer.Context,
    id: str = id_or_name("repositories"),
    remote: Optional[str] = typer.Option(None, help="Optional remote id to use for sync."),
) -> None:
    """Sync a repository."""
    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{id}/sync/")
        handle_response(ctx.obj, resp)


@app.command()
def publish(
    ctx: typer.Context,
    id: str = id_or_name("repositories"),
    force: bool = typer.Option(
        False, "--force", help="Force publish even if there are no changes."
    ),
) -> None:
    """Publish a repository making its packages available and updating its metadata."""
    with get_client(ctx.obj) as client:
        resp = client.post(f"/repositories/{id}/publish/", json={"force": force})
        handle_response(ctx.obj, resp)


@packages.command(name="update")
def update_packages(
    ctx: typer.Context,
    repo_id: str = id_or_name("repositories"),
    release: str = typer.Argument(None, help=RELEASE_HELP),
    # We always use the default component, don't expose that unnecessary complication to the user.
    # component: str = typer.Argument(None, help="Component to add packages to."),
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
    # if component:
    #    data["component"] = component

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/repositories/{repo_id}/packages/", json=data)
        handle_response(ctx.obj, resp)

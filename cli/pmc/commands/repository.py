from typing import Any, Dict, List, Optional, Union

import typer

from pmc.client import client, handle_response, poll_task
from pmc.commands.release import releases
from pmc.commands.repo_version import version
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import (
    LIMIT_OPT,
    OFFSET_OPT,
    ORDERING_OPT,
    DistroType,
    RepoSigningService,
    RepoType,
)
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

app = UserFriendlyTyper()
packages = UserFriendlyTyper(help="Manage a repo's packages.")
app.add_typer(packages, name="package")
app.add_typer(releases, name="release")
app.add_restricted_typer(version, name="version")

ADD_PACKAGES_HELP = f"{LIST_SEPARATOR.title}-separated list of package ids to add."
REMOVE_PACKAGES_HELP = f"{LIST_SEPARATOR.title}-separated list of package ids to remove."
RELEASE_HELP = (
    "Name of the apt release whose packages you're managing. "
    "Release is required if you're adding packages to an apt repo, or removing packages from a "
    "specific apt release only. "
    "You can also remove the packages from ALL releases in an apt repo by not specifying it in "
    "a remove operation. "
    "This option does nothing for yum repos."
)
RETAIN_REPO_VERSIONS_HELP = (
    "The number of repository versions to retain. Pass an empty string to retain all. "
    "Default is all."
)
SUPERUSER_HELP = "Override package permission check. Available only to repo operators."

sqlite_metadata_option = typer.Option(
    None, help="Enable the generation of sqlite metadata files for yum repos (Deprecated)."
)


@app.command()
def list(
    ctx: typer.Context,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    name: Optional[str] = typer.Option(None),
    name_contains: Optional[str] = typer.Option(
        None, help="Filter repos with names that contain string."
    ),
    name_icontains: Optional[str] = typer.Option(
        None, help="Filter repos with names that contain string (case insensitive)."
    ),
    ordering: str = ORDERING_OPT,
) -> None:
    """List repositories."""
    params = build_params(
        limit,
        offset,
        name=name,
        name__contains=name_contains,
        name__icontains=name_icontains,
        ordering=ordering,
    )

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
        None, help=f"{LIST_SEPARATOR.title}-separated list of release names"
    ),
    paths: Optional[str] = typer.Option(
        None, help=f"{LIST_SEPARATOR.title}-separated list of distribution paths"
    ),
    sqlite_metadata: Optional[bool] = sqlite_metadata_option,
    retain_repo_versions: Optional[int] = typer.Option(None, help=RETAIN_REPO_VERSIONS_HELP),
) -> None:
    """Create a repository."""
    data = {
        "name": name,
        "type": repo_type,
        "remote": remote,
        "retain_repo_versions": retain_repo_versions,
    }

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

    repo_resp = client.post("/repositories/", json=data)
    handle_response(ctx.obj, repo_resp)
    repo_id = repo_resp.json()["id"]

    if releases:
        for release in releases.split(LIST_SEPARATOR):
            if not ctx.obj.quiet:
                typer.echo(f"Creating release '{release}'.", err=True)
            resp = client.post(f"/repositories/{repo_id}/releases/", json={"name": release})
            poll_task(resp.json().get("task"), quiet=ctx.obj.quiet)

    if paths:
        for path in paths.split(LIST_SEPARATOR):
            if not ctx.obj.quiet:
                typer.echo(f"Creating distribution '{path}'.", err=True)
            distro = {
                "repository": repo_id,
                "type": DistroType[repo_type],
                "name": path,
                "base_path": path,
            }
            resp = client.post("/distributions/", json=distro)
            poll_task(resp.json().get("task"), quiet=ctx.obj.quiet)


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("repositories")) -> None:
    """Show details for a particular repository."""
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
    retain_repo_versions: Optional[str] = typer.Option(None, help=RETAIN_REPO_VERSIONS_HELP),
) -> None:
    """Update a repository."""

    def show_func(task: Any) -> Any:
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
    if retain_repo_versions is not None:
        if retain_repo_versions == "":
            data["retain_repo_versions"] = None  # unset retain_repo_versions
        else:
            try:
                data["retain_repo_versions"] = int(retain_repo_versions)
            except ValueError:
                raise typer.BadParameter(f"'{retain_repo_versions}' is not a valid integer.")

    resp = client.patch(f"/repositories/{id}/", json=data)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.restricted_command()
def delete(ctx: typer.Context, id: str = id_or_name("repositories")) -> None:
    """Delete a repository."""
    resp = client.delete(f"/repositories/{id}/")
    handle_response(ctx.obj, resp)


@app.restricted_command()
def sync(
    ctx: typer.Context,
    id: str = id_or_name("repositories"),
    remote: Optional[str] = typer.Option(None, help="Optional remote id to use for sync."),
) -> None:
    """Sync a repository."""
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
    superuser: bool = typer.Option(False, help=SUPERUSER_HELP),
) -> None:
    """Add or remove packages from a repository."""
    data: Dict[str, Union[str, List[str], bool]] = {}
    if add_packages:
        data["add_packages"] = add_packages.split(LIST_SEPARATOR)
    if remove_packages:
        data["remove_packages"] = remove_packages.split(LIST_SEPARATOR)
    if release:
        data["release"] = release
    if superuser:
        data["superuser"] = superuser
    # if component:
    #    data["component"] = component

    resp = client.patch(f"/repositories/{repo_id}/packages/", json=data)
    handle_response(ctx.obj, resp)


@app.command()
def purge(
    ctx: typer.Context,
    repo_id: str = id_or_name("repositories"),
    release: str = typer.Argument(
        None, help="Only delete packages from this release (deb repos only)"
    ),
    confirm: bool = typer.Option(False),
    superuser: bool = typer.Option(False, help=SUPERUSER_HELP),
) -> None:
    if not confirm:
        if not typer.confirm("This will delete all content in the specified repo. Proceed?"):
            typer.echo("Not confirmed. Exiting.", err=True)
            return

    params: Dict[str, Any] = {"all": True}
    if release:
        params["release"] = release
    if superuser:
        params["superuser"] = superuser
    resp = client.patch(f"/repositories/{repo_id}/bulk_delete/", json=params)
    handle_response(ctx.obj, resp)


# TODO: [MIGRATE] remove these lines
@app.restricted_command()
def migration_failures(
    ctx: typer.Context,
    retry: Optional[bool] = typer.Option(False),
) -> None:
    """
    List [default] or retry a batch of 10 failing migration messages.
    Wait 5 seconds between requests so the messages become available again.
    """
    args = {}
    if retry:
        args["retry"] = True
    resp = client.post("/repositories/migration_failures/", params=args)
    handle_response(ctx.obj, resp)


# END [MIGRATE]

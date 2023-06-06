import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from click import BadParameter

from pmc.artifact_uploader import ArtifactUploader
from pmc.client import client, handle_response, output_json
from pmc.commands.repository import update_packages
from pmc.constants import LIST_SEPARATOR, NamedString
from pmc.context import PMCContext
from pmc.package_uploader import PackageUploader
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, ORDERING_OPT, PackageType
from pmc.utils import UserFriendlyTyper, build_params, id_or_name

app = UserFriendlyTyper()
deb = UserFriendlyTyper()
deb_src = UserFriendlyTyper()
rpm = UserFriendlyTyper()
python = UserFriendlyTyper()
file = UserFriendlyTyper()

app.add_typer(deb, name="deb", help="Manage deb packages")
app.add_typer(deb_src, name="debsrc", help="Manage deb source packages")
app.add_typer(rpm, name="rpm", help="Manage rpm packages")
app.add_restricted_typer(python, name="python", help="Manage python packages")
app.add_restricted_typer(file, name="file", help="Manage files")

name_option = typer.Option(None, help="Name of the packages.")
repo_option = typer.Option(
    None, "--repository", "--repo", help="Id or Name of the repo that contains the packages."
)
sha256_option = typer.Option(None, help="Sha256 sum of the file in question.")
file_option = typer.Option(
    None,
    help="Path to the local file you're searching for. Calculates sha256 sum and uses that filter.",
    exists=True,
    readable=True,
    dir_okay=False,
)
package_arg = typer.Argument(
    ..., help="URL to a package, path to a package, or path to a directory of packages."
)


def _sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for line in f:
            h.update(line)
    return h.hexdigest()


def _list(package_type: PackageType, ctx: typer.Context, params: Dict[str, Any]) -> None:
    # filter out null values
    params = build_params(**params)
    resp = client.get(f"/{package_type}/packages/", params=params)
    handle_response(ctx.obj, resp)


@deb.command(name="list")
def deb_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    release: Optional[str] = id_or_name(
        "repositories/%(repository)s/releases",
        typer.Option(None, help="Name or Id. Only list packages in this apt release."),
    ),
    name: Optional[str] = name_option,
    version: Optional[str] = typer.Option(None),
    arch: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    relative_path: Optional[str] = typer.Option(None),
    file: Optional[Path] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    ordering: str = ORDERING_OPT,
) -> None:
    """List deb packages."""
    if file:
        sha256 = _sha256sum(file)
    params = build_params(
        limit,
        offset,
        ordering=ordering,
        repository=repository,
        release=release,
        package=name,
        version=version,
        architecture=arch,
        sha256=sha256,
        relative_path=relative_path,
    )
    _list(PackageType.deb, ctx, params)


@deb_src.command(name="list")
def deb_src_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    release: Optional[str] = id_or_name(
        "repositories/%(repository)s/releases",
        typer.Option(None, help="Name or Id. Only list packages in this apt release."),
    ),
    name: Optional[str] = name_option,
    version: Optional[str] = typer.Option(None),
    arch: Optional[str] = typer.Option(None),
    relative_path: Optional[str] = typer.Option(None),
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    ordering: str = ORDERING_OPT,
) -> None:
    """
    List debian source packages matching the specified optional filters.

    \b
    - pmc package debsrc list
    - pmc package debsrc list --version=2.10-2ubuntu2
    """
    params = build_params(
        limit,
        offset,
        ordering=ordering,
        repository=repository,
        release=release,
        source=name,
        version=version,
        architecture=arch,
        relative_path=relative_path,
    )
    _list(PackageType.deb_src, ctx, params)


@rpm.command(name="list")
def rpm_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    name: Optional[str] = name_option,
    epoch: Optional[str] = typer.Option(None),
    version: Optional[str] = typer.Option(None),
    release: Optional[str] = typer.Option(None),
    arch: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    file: Optional[Path] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    ordering: str = ORDERING_OPT,
) -> None:
    """List rpm packages."""
    if file:
        sha256 = _sha256sum(file)

    params = build_params(
        limit,
        offset,
        ordering=ordering,
        repository=repository,
        release=release,
        name=name,
        epoch=epoch,
        version=version,
        arch=arch,
        sha256=sha256,
    )
    _list(PackageType.rpm, ctx, params)


@python.command(name="list")
def python_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    name: Optional[str] = typer.Option(None),
    filename: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    file: Optional[Path] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    ordering: str = ORDERING_OPT,
) -> None:
    """List python packages."""
    if file:
        sha256 = _sha256sum(file)

    params = build_params(
        limit,
        offset,
        ordering=ordering,
        repository=repository,
        name=name,
        filename=filename,
        sha256=sha256,
    )
    _list(PackageType.python, ctx, params)


@file.command(name="list")
def file_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    relative_path: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    file: Optional[Path] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    ordering: str = ORDERING_OPT,
) -> None:
    """List files."""
    if file:
        sha256 = _sha256sum(file)

    params = build_params(
        limit,
        offset,
        ordering=ordering,
        repository=repository,
        relative_path=relative_path,
        sha256=sha256,
    )
    _list(PackageType.file, ctx, params)


@app.command()
def upload(
    ctx: typer.Context,
    package: str = package_arg,
    ignore_signature: bool = typer.Option(
        False,
        "--ignore-signature",
        show_default=False,
        help="Ignore the signature check. Only allowable for legacy packages.",
    ),
    file_type: Optional[PackageType] = typer.Option(
        None,
        "--type",
        "-t",
        help=(
            "Manually specify the type of file being uploaded. Otherwise the file's extension "
            "is used to guess the file type."
        ),
    ),
    relative_path: Optional[str] = typer.Option(
        None, help="Manually specify the relative path of the package (files packages only)."
    ),
    source_artifact: Optional[List[str]] = typer.Option(
        None,
        help="URL to an artifact, path to an artifact, or path to a directory of artifacts.",
    ),
) -> None:
    """Upload a package."""
    if source_artifact:
        for artifact in source_artifact:
            artifact_uploader = ArtifactUploader(ctx.obj, artifact)
            artifact_uploader.upload()

    uploader = PackageUploader(ctx.obj, package, ignore_signature, file_type, relative_path)
    packages = uploader.upload()
    if ctx.obj.id_only and len(packages) == 1:
        typer.echo(packages[0]["id"])
    else:
        output_json(ctx.obj, packages)


@app.command()
def upload_and_add(
    ctx: typer.Context,
    package: str = package_arg,
    repositories: str = typer.Argument(
        ...,
        help=f"{LIST_SEPARATOR.Name}-separated list of repository names or ids to push to,"
        " and in the case of apt repos it must be <name_or_id>=<release>. See usage examples.",
    ),
) -> None:
    """
    Upload and add package(s) into the given repo(s). This allows you to add multiple packages to
    multiple repos without having to keep track of package ids. This is not an atomic transaction,
    so if it fails you can get into a partially-completed state. This essentially just calls out to
    two other commands in sequence using default options:

    \b
    1. pmc package upload
    2. pmc repo package update

    You should only upload packages / interact with repos of one type at a time, eg only rpms or
    only debs. Usage examples:

    \b
    RPM:
      pmc package upload-and-add kernel.rpm my-repo-yum
      pmc package upload-and-add rpms/ "my-repo-1-yum,my-repo-2-yum,my-repo-3-yum"
      pmc package upload-and-add kernel.rpm repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4
    DEB:
      pmc package upload-and-add kernel.deb "my-repo-apt=jammy"
      pmc package upload-and-add debs/ "my-repo-1-apt=jammy,my-repo-1-apt=focal,my-repo-2-apt=bullseye"
      pmc package upload-and-add debs/ "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558=jammy"
    """  # noqa: E501

    pmc_ctx: PMCContext = ctx.obj
    pmc_ctx.config.id_only = False
    pmc_ctx.config.no_wait = False

    # Step 0: Look up repo ids and do basic input validation.
    repo_release_list = repositories.split(LIST_SEPARATOR)
    repos_and_releases = [x.split("=") for x in repo_release_list]
    if all(len(x) == 1 for x in repos_and_releases):
        file_type = PackageType("rpm")
        # normalize with empty release
        repos_and_releases = [[x[0], ""] for x in repos_and_releases]
    elif all(len(x) == 2 for x in repos_and_releases):
        file_type = PackageType("deb")
    else:
        raise BadParameter(
            "Unparsable repository list. Must be only-yum or only-apt repos, and all apt repos"
            " must have exactly one release per listed reference (e.g. if you want to add the"
            " package to two releases in the repo, list it twice: Repo=Release1,Repo=Release2).",
        )

    # We don't get the magic "name or id" translation if we call the function directly, so do it
    # manually.
    field = NamedString("repositories", name="repositories")
    lookup = id_or_name("repositories")
    repos = [(lookup.callback(ctx, field, repo), release) for repo, release in repos_and_releases]

    # Step 1: Upload the packages.
    typer.echo("Uploading package(s)...", err=True)
    # Setting the file_type explicitly here causes errors if packages that don't match with the
    # repo type are mixed in, which we want.
    uploader = PackageUploader(ctx.obj, package, False, file_type=file_type, relative_path=None)
    packages = uploader.upload()
    package_ids = LIST_SEPARATOR.join([x["id"] for x in packages])

    # Step 2: Update the repos.
    typer.echo("Updating repos(s)...", err=True)
    for repo, release in repos:
        update_packages(
            ctx, repo, release, add_packages=package_ids, remove_packages=None, superuser=False
        )


@app.command()
def show(
    ctx: typer.Context,
    id: str,
    details: bool = typer.Option(False, help="Show extra package details"),
) -> None:
    """Show details for a particular package."""
    resp = client.get(f"/packages/{id}/", params={"details": details})
    handle_response(ctx.obj, resp)

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from pmc.artifact_uploader import ArtifactUploader
from pmc.client import client, handle_response, output_json
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
    package: str = typer.Argument(
        ..., help="URL to a package, path to a package, or path to a directory of packages."
    ),
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
def show(
    ctx: typer.Context,
    id: str,
    details: bool = typer.Option(False, help="Show extra package details"),
) -> None:
    """Show details for a particular package."""
    resp = client.get(f"/packages/{id}/", params={"details": details})
    handle_response(ctx.obj, resp)

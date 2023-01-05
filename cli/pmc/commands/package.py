import hashlib
from typing import Any, Dict, Optional

import typer
from click import BadParameter
from pydantic import AnyHttpUrl, ValidationError, parse_obj_as

from pmc.client import client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, PackageType
from pmc.utils import UserFriendlyTyper, id_or_name, raise_if_task_failed

app = UserFriendlyTyper()
deb = UserFriendlyTyper()
rpm = UserFriendlyTyper()
python = UserFriendlyTyper()
file = UserFriendlyTyper()

app.add_typer(deb, name="deb", help="Manage deb packages")
app.add_typer(rpm, name="rpm", help="Manage rpm packages")
app.add_typer(python, name="python", help="Manage python packages")
app.add_typer(file, name="file", help="Manage files")

name_option = typer.Option(None, help="Name of the packages.")
repo_option = typer.Option(
    None, "--repository", "--repo", help="Id or Name of the repo that contains the packages."
)
sha256_option = typer.Option(None, help="Sha256 sum of the file in question.")
file_option = typer.Option(
    None,
    help="Path to the local file you're searching for. Calculates sha256 sum and uses that filter.",
)


def _sha256sum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f:
            h.update(line)
    return h.hexdigest()


def _list(package_type: PackageType, ctx: typer.Context, params: Dict[str, Any]) -> None:
    # filter out null values
    params = {key: val for key, val in params.items() if val is not None}
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
    file: Optional[str] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List deb packages."""
    if file:
        sha256 = _sha256sum(file)
    params = {
        "repository": repository,
        "release": release,
        "package": name,
        "version": version,
        "architecture": arch,
        "sha256": sha256,
        "limit": limit,
        "offset": offset,
    }
    _list(PackageType.deb, ctx, params)


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
    file: Optional[str] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List rpm packages."""
    if file:
        sha256 = _sha256sum(file)
    params = {
        "repository": repository,
        "name": name,
        "version": version,
        "arch": arch,
        "release": release,
        "epoch": epoch,
        "sha256": sha256,
        "limit": limit,
        "offset": offset,
    }
    _list(PackageType.rpm, ctx, params)


@python.command(name="list")
def python_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    name: Optional[str] = typer.Option(None),
    filename: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    file: Optional[str] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List python packages."""
    if file:
        sha256 = _sha256sum(file)
    params = {
        "repository": repository,
        "name": name,
        "filename": filename,
        "sha256": sha256,
        "limit": limit,
        "offset": offset,
    }
    _list(PackageType.python, ctx, params)


@file.command(name="list")
def file_list(
    ctx: typer.Context,
    repository: Optional[str] = id_or_name("repositories", repo_option),
    relative_path: Optional[str] = typer.Option(None),
    sha256: Optional[str] = sha256_option,
    file: Optional[str] = file_option,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
) -> None:
    """List files."""
    if file:
        sha256 = _sha256sum(file)
    params = {
        "repository": repository,
        "relative_path": relative_path,
        "sha256": sha256,
        "limit": limit,
        "offset": offset,
    }
    _list(PackageType.file, ctx, params)


@app.command()
def upload(
    ctx: typer.Context,
    package: str = typer.Argument(..., help="Path or url to package"),
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
) -> None:
    """Upload a package."""

    def show_func(task: Any) -> Any:
        raise_if_task_failed(task)
        package_id = task["created_resources"][0]
        return client.get(f"/packages/{package_id}/")

    data: Dict[str, Any] = {"ignore_signature": ignore_signature}
    files = None

    try:
        data["url"] = parse_obj_as(AnyHttpUrl, package)
    except ValidationError:
        try:
            files = {"file": open(package, "rb")}
        except FileNotFoundError:
            raise BadParameter("Invalid path/url for package argument.")

    if file_type:
        data["file_type"] = file_type
    if relative_path:
        data["relative_path"] = relative_path

    resp = client.post("/packages/", params=data, files=files)
    handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(
    ctx: typer.Context,
    id: str,
    details: bool = typer.Option(False, help="Show extra package details"),
) -> None:
    """Show details for a particular package."""
    resp = client.get(f"/packages/{id}/", params={"details": details})
    handle_response(ctx.obj, resp)

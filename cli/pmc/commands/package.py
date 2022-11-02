from typing import Any, Dict, Optional

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, PackageType
from pmc.utils import UserFriendlyTyper, raise_if_task_failed

app = UserFriendlyTyper()
deb = UserFriendlyTyper()
rpm = UserFriendlyTyper()
python = UserFriendlyTyper()
file = UserFriendlyTyper()

app.add_typer(deb, name="deb", help="Manage deb packages")
app.add_typer(rpm, name="rpm", help="Manage rpm packages")
app.add_typer(python, name="python", help="Manage python packages")
app.add_typer(file, name="file", help="Manage files")


def _list(package_type: PackageType, ctx: typer.Context, limit: int, offset: int) -> None:
    params: Dict[str, Any] = dict(limit=limit, offset=offset)
    with get_client(ctx.obj) as client:
        resp = client.get(f"/{package_type}/packages/", params=params)
        handle_response(ctx.obj, resp)


@deb.command(name="list")
def deb_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List deb packages."""
    _list(PackageType.deb, ctx, limit, offset)


@rpm.command(name="list")
def rpm_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List rpm packages."""
    _list(PackageType.rpm, ctx, limit, offset)


@python.command(name="list")
def python_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List python packages."""
    _list(PackageType.python, ctx, limit, offset)


@file.command(name="list")
def file_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List files."""
    _list(PackageType.file, ctx, limit, offset)


@app.command()
def upload(
    ctx: typer.Context,
    file: typer.FileBinaryRead,
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
        with get_client(ctx.obj) as client:
            return client.get(f"/packages/{package_id}/")

    data: Dict[str, Any] = {"ignore_signature": ignore_signature}
    if file_type:
        data["file_type"] = file_type
    if relative_path:
        data["relative_path"] = relative_path
    files = {"file": file}

    with get_client(ctx.obj) as client:
        resp = client.post("/packages/", params=data, files=files)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(
    ctx: typer.Context,
    id: str,
    details: bool = typer.Option(False, help="Show extra package details"),
) -> None:
    """Show details for a particular package."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/packages/{id}/", params={"details": details})
        handle_response(ctx.obj, resp)

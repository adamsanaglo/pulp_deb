from typing import Any, Dict

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, PackageType
from pmc.utils import raise_if_task_failed

app = typer.Typer()
deb = typer.Typer()
rpm = typer.Typer()
app.add_typer(deb, name="deb", help="Manage deb packages")
app.add_typer(rpm, name="rpm", help="Manage rpm packages")


def _list(type: PackageType, ctx: typer.Context, limit: int, offset: int) -> None:
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get(f"/{type}/packages/", params=params)
        handle_response(ctx.obj, resp)


@deb.command(name="list")
def deb_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List deb packages."""
    _list(PackageType.deb, ctx, limit, offset)


@rpm.command(name="list")
def rpm_list(ctx: typer.Context, limit: int = LIMIT_OPT, offset: int = OFFSET_OPT) -> None:
    """List rpm packages."""
    _list(PackageType.rpm, ctx, limit, offset)


@app.command()
def upload(
    ctx: typer.Context,
    file: typer.FileBinaryRead,
    force_name: bool = typer.Option(
        False,
        "--force-name",
        show_default=False,
        help="Force the current filename to persist, and not be reset to standard naming "
        "conventions. We recommend you do NOT set this unless you have a good reason.",
    ),
    ignore_signature: bool = typer.Option(
        False,
        "--ignore-signature",
        show_default=False,
        help="Ignore the signature check. Only allowable for legacy packages.",
    ),
) -> None:
    """Upload a package."""

    def show_func(task: Any) -> Any:
        raise_if_task_failed(task)
        package_id = task["created_resources"][0]
        with get_client(ctx.obj) as client:
            return client.get(f"/packages/{package_id}/")

    data = {"force_name": force_name, "ignore_signature": ignore_signature}
    files = {"file": file}
    with get_client(ctx.obj) as client:
        resp = client.post("/packages/", params=data, files=files)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular package."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/packages/{id}/")
        handle_response(ctx.obj, resp)

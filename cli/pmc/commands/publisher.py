from typing import Any, Dict, Optional

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT

app = typer.Typer()


PUBLISHER_FIELDS = {
    "name",
    "is_enabled",
    "is_account_admin",
    "is_repo_admin",
    "is_package_admin",
    "icm_service",
    "icm_team",
    "contact_email",
}


@app.command()
def list(
    ctx: typer.Context,
    limit: Optional[int] = LIMIT_OPT,
    offset: Optional[int] = OFFSET_OPT,
) -> None:
    """List publishers."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get("/publishers/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
def create(
    ctx: typer.Context,
    name: str,
    contact_email: str,
    icm_service: str,
    icm_team: str,
    is_enabled: bool = typer.Option(True, "--enabled/--disabled"),
    is_account_admin: bool = typer.Option(False),
    is_repo_admin: bool = typer.Option(False),
    is_package_admin: bool = typer.Option(False),
) -> None:
    """Create a publisher."""
    ld = locals()
    data = {field: ld[field] for field in PUBLISHER_FIELDS}

    with get_client(ctx.obj) as client:
        resp = client.post("/publishers/", json=data)
        handle_response(ctx.obj, resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular publisher."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/publishers/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def update(
    ctx: typer.Context,
    id: str,
    name: str = typer.Option(None),
    is_enabled: bool = typer.Option(None, "--enabled/--disabled"),
    is_account_admin: bool = typer.Option(None),
    is_repo_admin: bool = typer.Option(None),
    is_package_admin: bool = typer.Option(None),
    icm_service: str = typer.Option(None),
    icm_team: str = typer.Option(None),
    contact_email: str = typer.Option(None),
) -> None:
    """Update a publisher."""
    ld = locals()
    data = {field: ld[field] for field in PUBLISHER_FIELDS if ld[field] is not None}

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/publishers/{id}/", json=data)
        handle_response(ctx.obj, resp)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a publisher."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/publishers/{id}/")
        handle_response(ctx.obj, resp)

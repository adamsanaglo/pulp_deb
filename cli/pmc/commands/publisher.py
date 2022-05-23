import typer

from pmc.client import get_client

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
def list(ctx: typer.Context) -> None:
    """List publishers."""
    with get_client(ctx.obj.config) as client:
        resp = client.get("/publishers/")
        ctx.obj.handle_response(resp)


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

    with get_client(ctx.obj.config) as client:
        resp = client.post("/publishers/", json=data)
        ctx.obj.handle_response(resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular publisher."""
    with get_client(ctx.obj.config) as client:
        resp = client.get(f"/publishers/{id}/")
        ctx.obj.handle_response(resp)


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

    with get_client(ctx.obj.config) as client:
        resp = client.patch(f"/publishers/{id}/", json=data)
        ctx.obj.handle_response(resp)


@app.command()
def delete(ctx: typer.Context, id: str) -> None:
    """Delete a publisher."""
    with get_client(ctx.obj.config) as client:
        resp = client.delete(f"/publishers/{id}/")
        ctx.obj.handle_response(resp)

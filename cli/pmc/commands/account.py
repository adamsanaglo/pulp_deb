from typing import Any, Dict, Optional

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, Role
from pmc.utils import id_or_name

app = typer.Typer()


ID_ARG = typer.Argument(
    ...,
    help="The Azure Active Directory 'oid' of the principal / account being operated on. "
    "https://docs.microsoft.com/en-us/azure/active-directory/develop/access-tokens#payload-claims",
)
NAME_HELP = "A human-helpful name for the account."
EMAIL_HELP = "Contact email(s) (full address, semicolon-separated) for this principal / account."
SERVICE_HELP = "Which IcM Service this account is associated with."
TEAM_HELP = "Which IcM Team this account is associated with."
ENABLED_HELP = "Disabled accounts are denied all access."
ROLE_HELP = "The access level of the account. All normal accounts will be 'Publisher'."

ACCOUNT_FIELDS = {
    "id",
    "name",
    "is_enabled",
    "role",
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
    """List accounts."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get("/accounts/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
def create(
    ctx: typer.Context,
    id: str = ID_ARG,
    name: str = typer.Argument(..., help=NAME_HELP),
    contact_email: str = typer.Argument(..., help=EMAIL_HELP),
    icm_service: str = typer.Argument(..., help=SERVICE_HELP),
    icm_team: str = typer.Argument(..., help=TEAM_HELP),
    is_enabled: bool = typer.Option(True, "--enabled/--disabled", help=ENABLED_HELP),
    role: Role = typer.Option(Role.Publisher, help=ROLE_HELP),
) -> None:
    """Create an account."""
    ld = locals()
    data = {field: ld[field] for field in ACCOUNT_FIELDS}

    with get_client(ctx.obj) as client:
        resp = client.post("/accounts/", json=data)
        handle_response(ctx.obj, resp)


@app.command()
def show(ctx: typer.Context, id: str = id_or_name("accounts", ID_ARG)) -> None:
    """Show details for a particular account."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/accounts/{id}/")
        handle_response(ctx.obj, resp)


@app.command()
def update(
    ctx: typer.Context,
    id: str = id_or_name("accounts", ID_ARG),
    name: str = typer.Option(None, help=NAME_HELP),
    is_enabled: bool = typer.Option(None, "--enabled/--disabled", help=ENABLED_HELP),
    icm_service: str = typer.Option(None, help=SERVICE_HELP),
    icm_team: str = typer.Option(None, help=TEAM_HELP),
    contact_email: str = typer.Option(None, help=EMAIL_HELP),
    role: str = typer.Option(None, help=ROLE_HELP),
) -> None:
    """Update an account."""
    ld = locals()
    data = {field: ld[field] for field in ACCOUNT_FIELDS if ld[field] is not None}

    with get_client(ctx.obj) as client:
        resp = client.patch(f"/accounts/{id}/", json=data)
        handle_response(ctx.obj, resp)


@app.command()
def delete(ctx: typer.Context, id: str = id_or_name("accounts", ID_ARG)) -> None:
    """Delete an account."""
    with get_client(ctx.obj) as client:
        resp = client.delete(f"/accounts/{id}/")
        handle_response(ctx.obj, resp)

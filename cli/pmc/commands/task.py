from typing import Any, Dict, Optional

import typer

from pmc.client import get_client, handle_response
from pmc.schemas import LIMIT_OPT, OFFSET_OPT
from pmc.utils import UserFriendlyTyper

app = UserFriendlyTyper()


@app.command()
def list(
    ctx: typer.Context, limit: Optional[int] = LIMIT_OPT, offset: Optional[int] = OFFSET_OPT
) -> None:
    """List tasks."""
    params: Dict[str, Any] = dict(limit=limit, offset=offset)

    with get_client(ctx.obj) as client:
        resp = client.get("/tasks/", params=params)
        handle_response(ctx.obj, resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular task."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/tasks/{id}/")
        handle_response(ctx.obj, resp)


@app.restricted_command()
def cancel(ctx: typer.Context, id: str) -> None:
    """Cancel a task."""
    with get_client(ctx.obj) as client:
        resp = client.patch(f"/tasks/{id}/cancel/")
        handle_response(ctx.obj, resp)

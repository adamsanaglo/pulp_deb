import typer

from pmc.client import client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.schemas import LIMIT_OPT, OFFSET_OPT, ORDERING_OPT, TaskState
from pmc.utils import UserFriendlyTyper, build_params

app = UserFriendlyTyper()


@app.command()
def list(
    ctx: typer.Context,
    limit: int = LIMIT_OPT,
    offset: int = OFFSET_OPT,
    reserved_resource: str = typer.Option(
        None, help=f"Filter by list of reserved resource records separated by '{LIST_SEPARATOR}'."
    ),
    state: TaskState = typer.Option(None, help="Filter by task state."),
    name: str = typer.Option(None, help="Filter tasks by name."),
    name_contains: str = typer.Option(
        None, help="Filter tasks which have names containing string."
    ),
    created_resource: str = typer.Option(
        None, help="Filter tasks which created a resource with id."
    ),
    ordering: str = ORDERING_OPT,
) -> None:
    """List tasks."""
    params = build_params(
        limit,
        offset,
        ordering=ordering,
        reserved_resources=reserved_resource,
        state=state,
        name=name,
        name__contains=name_contains,
        created_resources=created_resource,
    )

    resp = client.get("/tasks/", params=params)
    handle_response(ctx.obj, resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular task."""
    resp = client.get(f"/tasks/{id}/")
    handle_response(ctx.obj, resp)


@app.restricted_command()
def cancel(ctx: typer.Context, id: str) -> None:
    """Cancel a task."""
    resp = client.patch(f"/tasks/{id}/cancel/")
    handle_response(ctx.obj, resp)

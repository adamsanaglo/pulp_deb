import typer

from pmc.client import get_client

app = typer.Typer()


@app.command()
def list(ctx: typer.Context) -> None:
    """List tasks."""
    with get_client(ctx.obj.config) as client:
        resp = client.get("/tasks/")
        ctx.obj.handle_response(resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular task."""
    with get_client(ctx.obj.config) as client:
        resp = client.get(f"/tasks/{id}/")
        ctx.obj.handle_response(resp)


@app.command()
def cancel(ctx: typer.Context, id: str) -> None:
    """Cancel a task."""
    with get_client(ctx.obj.config) as client:
        resp = client.patch(f"/tasks/{id}/cancel/")
        ctx.obj.handle_response(resp)

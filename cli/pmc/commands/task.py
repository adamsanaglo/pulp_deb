import typer

from pmc.client import client

app = typer.Typer()


@app.command()
def list(ctx: typer.Context) -> None:
    """List tasks."""
    resp = client.get("/tasks/")
    ctx.obj.handle_response(resp)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular task."""
    resp = client.get(f"/tasks/{id}/")
    ctx.obj.handle_response(resp)

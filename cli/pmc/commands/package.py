from typing import Any

import typer

from pmc.client import client

app = typer.Typer()


@app.command()
def list(ctx: typer.Context) -> None:
    """List packages."""
    resp = client.get("/packages/")
    ctx.obj.handle_response(resp)


@app.command()
def upload(ctx: typer.Context, file: typer.FileBinaryRead) -> None:
    """Upload a package."""

    def show_func(task: Any) -> Any:
        package_id = task["created_resources"][0]
        return client.get(f"/packages/{package_id}/")

    files = {"file": file}
    resp = client.post("/packages/", files=files)
    ctx.obj.handle_response(resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular package."""
    resp = client.get(f"/packages/{id}/")
    ctx.obj.handle_response(resp)

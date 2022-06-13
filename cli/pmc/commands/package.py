from typing import Any

import typer

from pmc.client import get_client, handle_response

app = typer.Typer()


@app.command()
def list(ctx: typer.Context) -> None:
    """List packages."""
    with get_client(ctx.obj) as client:
        resp = client.get("/packages/")
        handle_response(ctx.obj, resp)


@app.command()
def upload(ctx: typer.Context, file: typer.FileBinaryRead) -> None:
    """Upload a package."""

    def show_func(task: Any) -> Any:
        package_id = task["created_resources"][0]
        with get_client(ctx.obj) as client:
            return client.get(f"/packages/{package_id}/")

    files = {"file": file}
    with get_client(ctx.obj) as client:
        resp = client.post("/packages/", files=files)
        handle_response(ctx.obj, resp, task_handler=show_func)


@app.command()
def show(ctx: typer.Context, id: str) -> None:
    """Show details for a particular package."""
    with get_client(ctx.obj) as client:
        resp = client.get(f"/packages/{id}/")
        handle_response(ctx.obj, resp)

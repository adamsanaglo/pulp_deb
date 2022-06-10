import typer

from pmc.client import get_client

app = typer.Typer(no_args_is_help=True)


@app.command()
def cleanup(ctx: typer.Context) -> None:
    """List packages."""
    with get_client(ctx.obj.config) as client:
        resp = client.post("/orphans/cleanup/")
        ctx.obj.handle_response(resp)

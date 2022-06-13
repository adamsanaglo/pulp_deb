import typer

from pmc.client import get_client, handle_response

app = typer.Typer(no_args_is_help=True)


@app.command()
def cleanup(ctx: typer.Context) -> None:
    """List packages."""
    with get_client(ctx.obj) as client:
        resp = client.post("/orphans/cleanup/")
        handle_response(ctx.obj, resp)

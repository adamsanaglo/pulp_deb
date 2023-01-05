import typer

from pmc.client import client, handle_response
from pmc.utils import UserFriendlyTyper

app = UserFriendlyTyper(no_args_is_help=True)


@app.command()
def cleanup(
    ctx: typer.Context,
    protection_time: int = typer.Option(
        None,
        show_default=False,
        help="Set time in minutes that new orphans are protected from being cleaned. WARNING: "
        "setting this too low can affect packages that are being used by still-running tasks",
    ),
) -> None:
    """Delete packages that are not in any Repos."""
    options = {}
    if protection_time is not None:
        options["protection_time"] = protection_time
    resp = client.post("/orphans/cleanup/", params=options)
    handle_response(ctx.obj, resp)

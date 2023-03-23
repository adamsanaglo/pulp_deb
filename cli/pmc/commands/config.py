import json
from pathlib import Path

import click
import tomli_w
import typer

from pmc.schemas import CONFIG_PATHS, Config, Format, RepoSigningService
from pmc.utils import UserFriendlyTyper

app = UserFriendlyTyper()


NO_WAIT_OPT = typer.Option(False, "--no-wait", help="Don't wait for any background tasks.")
NO_COLOR_OPT = typer.Option(False, "--no-color", help="Suppress color output if enabled.")
PAGER_OPT = typer.Option(
    False, "--pager", help="Display output using a pager when it exceeds console height."
)
ID_ONLY_OPT = typer.Option(False, "--id-only", help="Show ids instead of full responses.")
DEBUG_OPT = typer.Option(False, "--debug", "-d", help="Show debug output.")
QUIET_OPT = typer.Option(
    False,
    "--quiet",
    "-q",
    help="Silence output except for warnings, errors, and the final command result.",
)
SSL_VERIFY_OPT = typer.Option(True, help="Verify the ssl cert.", hidden=True)
RESP_FORMAT_OPT = typer.Option(Format.json, "--format", hidden=True)  # TODO: add more formats
BASE_URL_OPT = typer.Option("", help="The base url of the server (i.e. https://<hostname>/api/v4)")
MSAL_CLIENT_ID_OPT = typer.Option(
    None,
    "--msal-client-id",
    help="Client ID for the account's Service Principal",
)
MSAL_SCOPE_OPT = typer.Option(
    None,
    "--msal-scope",
    help="Scope for authentication (i.e. api://13ab6030...)",
)
MSAL_CERT_PATH_OPT = typer.Option(
    None,
    "--msal-cert-path",
    help=(
        "Path to authentication cert for account's Service Principal. "
        "The cert contents can also be exported to an environment "
        "variable 'PMC_CLI_MSAL_CERT'."
    ),
)
MSAL_SNI_AUTH_OPT = typer.Option(
    True,
    help="Use SNI Authentication, which enables certificate auto-rotation.",
)
MSAL_AUTHORITY_OPT = typer.Option(
    None,
    "--msal-authority",
    help="Authority URL for authentication (i.e. https://login.microsoftonline.com/...)",
)


@app.command()
def create(
    ctx: typer.Context,
    location: Path = typer.Option(CONFIG_PATHS[0]),
    profile: str = typer.Option("default", help="Name of the profile to create."),
    edit: bool = typer.Option(True, help="Open the file for editing after creating it."),
    overwrite: bool = typer.Option(False, help="Overwrite the existing config."),
    no_wait: bool = NO_WAIT_OPT,
    no_color: bool = NO_COLOR_OPT,
    pager: bool = PAGER_OPT,
    id_only: bool = ID_ONLY_OPT,
    debug: bool = DEBUG_OPT,
    quiet: bool = QUIET_OPT,
    ssl_verify: bool = SSL_VERIFY_OPT,
    resp_format: Format = RESP_FORMAT_OPT,
    base_url: str = BASE_URL_OPT,
    msal_client_id: str = MSAL_CLIENT_ID_OPT,
    msal_scope: str = MSAL_SCOPE_OPT,
    msal_cert_path: Path = MSAL_CERT_PATH_OPT,
    msal_SNIAuth: bool = MSAL_SNI_AUTH_OPT,
    msal_authority: str = MSAL_AUTHORITY_OPT,
    signing_service: RepoSigningService = typer.Option(
        RepoSigningService.esrp, help="Default service to use when creating repos."
    ),
    hide_restricted_commands: bool = typer.Option(
        True,
        "--hide-restricted-commands/--show-restricted-commands",
        help="Whether to show restricted commands.",
    ),
) -> None:
    """Create a basic config and open it for editing."""
    config = {}
    location = location.expanduser()
    for key, field in Config.schema()["properties"].items():
        if key == "msal_cert":
            continue

        if locals().get(key):
            config[key] = locals()[key]
        else:
            config[key] = field.get("default", "FILL_ME_IN")

    # convert path into a string
    config["msal_cert_path"] = str(config["msal_cert_path"])

    if location.is_file() and not overwrite:
        raise click.UsageError(f"file '{location}' already exists.")

    # create the parent folder if necessary
    location.parents[0].mkdir(parents=True, exist_ok=True)

    if location.suffix == ".toml":
        with location.open("wb") as f:
            tomli_w.dump({profile: config}, f)
    elif location.suffix == ".json":
        with location.open("w") as f:
            json.dump(config, f, indent=3)
    else:
        raise click.UsageError(f"invalid file extension for '{location}'.")

    if edit:
        click.edit(filename=str(location))


@app.command()
def edit(ctx: typer.Context) -> None:
    """Edit config in a text editor."""
    config_path = ctx.find_root().params["config_path"]
    if not config_path:
        raise click.UsageError("config file not provided.")
    if not config_path.is_file():
        raise click.UsageError(f"location '{config_path}' is not a file.")

    click.edit(filename=str(config_path))

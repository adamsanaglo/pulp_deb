import json
from pathlib import Path

import click
import tomli_w
import typer

from pmc.schemas import CONFIG_PATHS, Config
from pmc.utils import UserFriendlyTyper, validate_config

app = UserFriendlyTyper()


def _edit_config(path: Path) -> None:
    """Open editor to edit config file and then validate the config."""
    click.edit(filename=str(path))
    validate_config(path)


@app.command()
def create(
    ctx: typer.Context,
    location: Path = typer.Option(CONFIG_PATHS[0]),
    edit: bool = typer.Option(True, help="Open the file for editing after creating it."),
    overwrite: bool = typer.Option(False, help="Overwrite the existing config."),
) -> None:
    """Create a basic config and open it for editing."""
    # create a default config
    default_config = {
        k: v.get("default", "FILL_ME_IN") for k, v in Config.schema()["properties"].items()
    }

    if location.is_file() and not overwrite:
        raise click.UsageError(f"file '{location}' already exists.")

    # create the parent folder if necessary
    location.parents[0].mkdir(parents=True, exist_ok=True)

    if location.suffix == ".toml":
        with location.open("wb") as f:
            tomli_w.dump({"cli": default_config}, f)
    elif location.suffix == ".json":
        with location.open("w") as f:
            json.dump(default_config, f, indent=3)
    else:
        raise click.UsageError(f"invalid file extension for '{location}'.")

    if edit:
        _edit_config(location)


@app.command()
def edit(ctx: typer.Context) -> None:
    """Edit config in a text editor."""
    config_path = ctx.find_root().params["config_path"]
    if not config_path:
        raise click.UsageError("config file not provided.")
    if not config_path.is_file():
        raise click.UsageError(f"location '{config_path}' is not a file.")

    _edit_config(config_path)

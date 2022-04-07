import json
from pathlib import Path

import click
import tomli_w
import typer

from pmc.schemas import CONFIG_PATHS, Config
from pmc.utils import validate_config

app = typer.Typer()


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
    config = Config()

    if location.is_file() and not overwrite:
        typer.echo(f"File '{location}' already exists.", err=True)
        raise typer.Exit(code=1)

    if location.suffix == ".toml":
        with location.open("wb") as f:
            tomli_w.dump({"cli": config.dict()}, f)
    elif location.suffix == ".json":
        with location.open("w") as f:
            json.dump(config.dict(), f, indent=3)
    else:
        typer.echo(f"Error: invalid file extension for '{location}'.", err=True)
        raise typer.Exit(code=1)

    if edit:
        _edit_config(location)


@app.command()
def edit(ctx: typer.Context) -> None:
    """Edit config in a text editor."""
    config_path = ctx.obj.config_path
    if not config_path:
        typer.echo("Error: config not found.", err=True)
        raise typer.Exit(code=1)
    if not config_path.is_file():
        typer.echo(f"Error: location '{config_path}' is not a file.", err=True)
        raise typer.Exit(code=1)

    _edit_config(config_path)

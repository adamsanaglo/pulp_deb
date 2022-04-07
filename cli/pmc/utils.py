import json
from pathlib import Path

import tomli
import typer
from pydantic import ValidationError

from pmc.schemas import Config


class UnsupportedFileType(Exception):
    pass


def parse_config(path: Path) -> Config:
    """
    Parse a config file at path and return Config.

    This function could raise UnsupportedFileType, JSONDecodeError, TOMLDecodeError, or a
    ValidationError.
    """
    with path.open("rb") as f:
        if path.suffix == ".json":
            settings = json.load(f)
        elif path.suffix == ".toml":
            settings = next(iter(tomli.load(f).values()), {})
        else:
            raise UnsupportedFileType

    return Config(**settings)


def validate_config(path: Path) -> None:
    """Validate config at path and handle any problems."""
    try:
        parse_config(path)
    except UnsupportedFileType:
        typer.echo(f"Unsupported file type for '{path}'.", err=True)
        raise typer.Exit(code=1)
    except (json.decoder.JSONDecodeError, tomli.TOMLDecodeError) as e:
        typer.echo(f"Parse error when parsing '{path}': {e}.", err=True)
        raise typer.Exit(code=1)
    except ValidationError as e:
        typer.echo(f"Invalid config '{path}': {e}", err=True)
        raise typer.Exit(code=1)

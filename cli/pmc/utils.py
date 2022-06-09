import json
from pathlib import Path

import tomli
from pydantic import ValidationError

from pmc.schemas import Config


class UnsupportedFileType(Exception):
    pass


class DecodeError(Exception):
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
            raise UnsupportedFileType(f"Unsupported file type for '{path}'.")

    return Config(**settings)


def validate_config(path: Path) -> None:
    """Validate config at path and handle any problems."""
    try:
        parse_config(path)
    except (json.decoder.JSONDecodeError, tomli.TOMLDecodeError, ValidationError) as e:
        raise DecodeError(f"Parse error when parsing '{path}': {e}.")

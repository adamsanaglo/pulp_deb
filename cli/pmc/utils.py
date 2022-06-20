import json
from pathlib import Path
from typing import Dict, Any

import tomli
from pydantic import ValidationError

from pmc.schemas import Config


PulpTask = Dict[str, Any]


class UnsupportedFileType(Exception):
    pass


class DecodeError(Exception):
    pass


class PulpTaskFailure(Exception):
    def __init__(self, task: PulpTask) -> None:
        error = task["error"]
        self.original_traceback = error["traceback"]
        self.original_message = error["description"]
        super().__init__()


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


def raise_if_task_failed(task: PulpTask) -> None:
    """Throw an appropriate error if the Pulp task failed."""
    if task["state"] == "failed":
        raise PulpTaskFailure(task)

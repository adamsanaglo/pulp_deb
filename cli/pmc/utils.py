import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Pattern, Union

import tomli
import typer
from pydantic import ValidationError

from pmc.client import get_client
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


def _lookup_id_or_name(
    resource: str, id_regex: Union[str, Pattern[str]], ctx: typer.Context, field: str, value: str
) -> str:
    if not value or re.match(id_regex, value):
        return value

    with get_client(ctx.obj) as client:
        resp = client.get(f"/{resource}/", params={"name": value})
        results = resp.json()
        if results["count"] == 1:
            return str(results["results"][0]["id"])
        else:
            raise Exception(f"Could not find resource with name '{value}'.")


def id_or_name(
    resource: str,
    param: Optional[typer.models.ParameterInfo] = None,
    id_regex: Union[str, Pattern[str]] = re.compile(
        "^[a-z-]*[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    ),
) -> Any:
    """Return a param with a callback that will accept id or name and return an id.

    The param argument should be a typer.Argument() or typer.Option().
    """

    def callback(ctx: typer.Context, field: str, val: str) -> str:
        return _lookup_id_or_name(resource, id_regex, ctx, field, val)

    if param is None:
        param = typer.Argument(..., help="An id or name for the resource.")

    assert param is not None
    param.callback = callback

    return param

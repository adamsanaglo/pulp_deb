import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Pattern, Union

import tomli
import typer

from pmc.client import get_client
from pmc.schemas import CONFIG_PATHS, Config

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


def resolve_config_path(value: Optional[Path]) -> Optional[Path]:
    path: Optional[Path] = None

    if value:
        if not value.is_file():
            raise ValueError(f"Error: file '{value}' does not exist or is not a file.")
        else:
            path = value
    else:
        path = next(filter(lambda fp: fp and fp.is_file(), CONFIG_PATHS), None)  # type: ignore

    return path


def _raw_config(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        if path.suffix == ".json":
            settings = json.load(f)
        elif path.suffix == ".toml":
            settings = next(iter(tomli.load(f).values()), {})
        else:
            raise UnsupportedFileType(f"Unsupported file type for '{path}'.")

    assert isinstance(settings, dict)
    return settings


def parse_config(path: Path) -> Config:
    """
    Parse a config file at path and return Config.

    This function could raise UnsupportedFileType, JSONDecodeError, TOMLDecodeError, or a
    ValidationError.
    """
    return Config(**_raw_config(path))


def validate_config(path: Path) -> None:
    """Validate config at path and handle any problems."""
    try:
        parse_config(path)
    except (json.decoder.JSONDecodeError, tomli.TOMLDecodeError) as e:
        raise DecodeError(f"Parse error when parsing '{path}': {e}.")


def raise_if_task_failed(task: PulpTask) -> None:
    """Throw an appropriate error if the Pulp task failed."""
    if task["state"] == "failed":
        raise PulpTaskFailure(task)


def _lookup_id_or_name(
    resource: str, id_regex: Union[str, Pattern[str]], ctx: typer.Context, field: str, value: str
) -> str:
    url = "/" + (resource % ctx.params) + "/"
    if not value or re.match(id_regex, value):
        return value

    with get_client(ctx.obj) as client:
        resp = client.get(url, params={"name": value})
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


@lru_cache
def _parse_restricted_commands() -> bool:
    # attempt to parse config for hide_restricted_commands
    path = None

    for opt in ["--config", "-c"]:
        # TODO: if we later add another "--config/-c" option this will pull this option value
        # we need to stop parsing args once we reach the first subcommand
        try:
            path = Path(sys.argv[sys.argv.index(opt) + 1])
            break
        except (ValueError, IndexError):
            continue
    path = resolve_config_path(path)

    if path:
        config = _raw_config(path)
        return config.get("hide_restricted_commands", True)

    return True


class UserFriendlyTyper(typer.Typer):
    """
    A Typer subclass that allows us to easily hide by default commands that Publishers are not
    allowed to run anyway, and is flexible about alternate names of commands if specified.
    """

    COMMAND_ALTERNATES = {
        "access": ["accesses"],
        "account": ["accounts"],
        "config": ["configs"],
        "deb": ["debs"],
        "distro": ["distros", "distribution", "distributions"],
        "orphan": ["orphans"],
        "package": ["packages"],
        "release": ["releases"],
        "remote": ["remotes"],
        "repo": ["repos", "repository", "repositories"],
        "rpm": ["rpms"],
        "task": ["tasks"],
    }

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        self.hide_restricted = _parse_restricted_commands()
        super().__init__(*args, **kwargs)

    def add_typer(self, *args, **kwargs) -> None:  # type: ignore
        """Add the command, and also add hidden alternates if specified."""
        super().add_typer(*args, **kwargs)

        if "name" in kwargs and kwargs["name"] in self.COMMAND_ALTERNATES:
            name = kwargs["name"]
            for alternate in self.COMMAND_ALTERNATES[name]:
                kwargs["name"] = alternate
                kwargs["hidden"] = True
                super().add_typer(*args, **kwargs)

    def add_restricted_typer(self, *args, **kwargs) -> None:  # type: ignore
        """Add a subcommand that is hidden by default."""
        if "hidden" not in kwargs:
            kwargs["hidden"] = self.hide_restricted
        self.add_typer(*args, **kwargs)

    def restricted_command(  # type: ignore
        self, *args, **kwargs
    ) -> Callable[[typer.models.CommandFunctionType], typer.models.CommandFunctionType]:
        """Add a command that is hidden by default."""
        if "hidden" not in kwargs:
            kwargs["hidden"] = self.hide_restricted
        return super().command(*args, **kwargs)

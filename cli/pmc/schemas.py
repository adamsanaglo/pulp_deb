from enum import Enum
from pathlib import Path

import click
from pydantic import BaseModel

FINISHED_TASK_STATES = ("skipped", "completed", "failed", "canceled")
CONFIG_PATHS = [
    Path(click.utils.get_app_dir("pmc"), "settings.toml"),
    Path(click.utils.get_app_dir("pmc"), "settings.json"),
]


class RepoType(str, Enum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class DistroType(str, Enum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class Format(str, Enum):
    """Options for different response formats (e.g. json)."""

    json = "json"

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class Config(BaseModel):
    no_wait: bool = False
    no_color: bool = False
    id_only: bool = False
    format: Format = Format.json

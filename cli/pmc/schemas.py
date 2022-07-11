from enum import Enum
from pathlib import Path

import click
import typer
from pydantic import AnyHttpUrl, BaseModel
from pydantic.tools import parse_obj_as

FINISHED_TASK_STATES = ("skipped", "completed", "failed", "canceled")
CONFIG_PATHS = [
    Path(click.utils.get_app_dir("pmc"), "settings.toml"),
    Path(click.utils.get_app_dir("pmc"), "settings.json"),
]
LIMIT_OPT = typer.Option(100, help="Limit on the number of results that are returned.")
OFFSET_OPT = typer.Option(0, help="Number of records to skip within set of results.")


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


class PackageType(str, Enum):
    """Type of packages."""

    deb = "deb"
    rpm = "rpm"

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class Format(str, Enum):
    """Options for different response formats (e.g. json)."""

    json = "json"

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


# Codebase uses typer to deconflict Config options and command-line parameters
# Any new options here MUST be added to main.py as well
class Config(BaseModel):
    no_wait: bool = False
    no_color: bool = False
    id_only: bool = False
    format: Format = Format.json
    debug: bool = False
    base_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "http://localhost:8000/api/v4")
    msal_client_id: str
    msal_scope: str
    msal_cert_path: Path
    msal_SNIAuth: bool = True
    msal_authority: str

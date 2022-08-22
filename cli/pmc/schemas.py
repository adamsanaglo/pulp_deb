from enum import Enum
from pathlib import Path

import click
import typer
from pydantic import AnyHttpUrl, BaseModel, FilePath, StrictStr, validator
from pydantic.tools import parse_obj_as

FINISHED_TASK_STATES = ("skipped", "completed", "failed", "canceled")
CONFIG_PATHS = [
    Path(click.utils.get_app_dir("pmc"), "settings.toml"),
    Path(click.utils.get_app_dir("pmc"), "settings.json"),
]
LIMIT_OPT = typer.Option(100, help="Limit on the number of results that are returned.")
OFFSET_OPT = typer.Option(0, help="Number of records to skip within set of results.")


class NonEmptyStr(StrictStr):
    min_length = 1


class StringEnum(str, Enum):
    def __str__(self) -> str:
        """Return value as the string representation."""
        return str(self.value)


class Role(StringEnum):
    # Another good candidate for consolidation with server.core.models.Role
    Publisher = "Publisher"
    Account_Admin = "Account_Admin"
    Repo_Admin = "Repo_Admin"
    Package_Admin = "Package_Admin"


class RepoType(StringEnum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class DistroType(StringEnum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class RemoteType(StringEnum):
    """Type for a remote."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class PackageType(StringEnum):
    """Type of packages."""

    deb = "deb"
    rpm = "rpm"


class Format(StringEnum):
    """Options for different response formats (e.g. json)."""

    json = "json"


# Codebase uses typer to define command-line parameters which doesn't support Pydantic (yet)
# Any new options here MUST be added to main.py as well until
# https://github.com/tiangolo/typer/issues/111 is supported
class Config(BaseModel):
    no_wait: bool = False
    no_color: bool = False
    id_only: bool = False
    format: Format = Format.json
    debug: bool = False
    base_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "http://localhost:8000/api/v4")
    msal_client_id: NonEmptyStr
    msal_scope: NonEmptyStr
    msal_cert_path: FilePath
    msal_SNIAuth: bool = True
    msal_authority: NonEmptyStr

    @validator("msal_cert_path", pre=True)
    def expand_path(cls, v: str) -> str:
        """Pre-validator to expand msal_cert_path."""
        try:
            path = Path(v).expanduser()
            return str(path)
        except Exception:
            # we encountered a problem; just use the original value and let validation handle it
            return v
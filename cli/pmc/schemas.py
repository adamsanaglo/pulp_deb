from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import click
import typer
from pydantic import AnyHttpUrl, BaseModel, FilePath, StrictStr, root_validator, validator
from pydantic.main import ModelMetaclass
from pydantic.tools import parse_obj_as

FINISHED_TASK_STATES = ("skipped", "completed", "failed", "canceled")
CONFIG_PATHS = [
    Path(click.utils.get_app_dir("pmc"), "settings.toml"),
    Path(click.utils.get_app_dir("pmc"), "settings.json"),
]
LIMIT_OPT = typer.Option(100, help="Limit on the number of results that are returned.")
OFFSET_OPT = typer.Option(0, help="Number of records to skip within set of results.")
ORDERING_OPT = typer.Option(
    None,
    help=(
        "Provide a field name to order the results in an ascending order by that field. "
        "Prefix a '-' to invert the order. Not all the fields are supported."
    ),
)


class NonEmptyStr(StrictStr):
    min_length = 1


class StringEnum(str, Enum):
    def __str__(self) -> str:
        """Return value as the string representation."""
        return str(self.value)


class OptionalFieldsMeta(ModelMetaclass):
    """
    Allows you to inherit all the attributes from another pydantic model but make them all optional.
    Must be used like this: "class NewClass(<InheritsFromBaseModel>, metaclass=OptionalFieldsMeta):"
    https://stackoverflow.com/questions/67699451/make-every-fields-as-optional-with-pydantic
    """

    def __new__(self, name, bases, namespaces, **kwargs):  # type: ignore
        annotations = namespaces.get("__annotations__", {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith("__"):
                annotations[field] = Optional[annotations[field]]
        namespaces["__annotations__"] = annotations
        return super().__new__(self, name, bases, namespaces, **kwargs)


class Role(StringEnum):
    # Another good candidate for consolidation with server.core.models.Role
    Publisher = "Publisher"
    Account_Admin = "Account_Admin"
    Repo_Admin = "Repo_Admin"
    Package_Admin = "Package_Admin"
    Migration = "Migration"  # TODO: [MIGRATE] remove this option


class RepoType(StringEnum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "python"
    file = "file"


class RepoSigningService(StringEnum):
    """The Signing Service to use for this repo."""

    legacy = "legacy"
    esrp = "esrp"


class DistroType(StringEnum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "pypi"
    file = "file"


class RemoteType(StringEnum):
    """Type for a remote."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class PackageType(StringEnum):
    """Type of packages."""

    deb = "deb"
    deb_src = "deb_src"
    rpm = "rpm"
    python = "python"
    file = "file"


class Format(StringEnum):
    """Options for different response formats (e.g. json)."""

    json = "json"


class TaskState(StringEnum):
    """Options for task state."""

    completed = "completed"
    failed = "failed"
    running = "running"
    waiting = "waiting"
    canceled = "canceled"
    canceling = "canceling"
    skipped = "skipped"


# Codebase uses typer to define command-line parameters which doesn't support Pydantic (yet)
# Any new options here MUST be added to main.py as well until
# https://github.com/tiangolo/typer/issues/111 is supported
class Config(BaseModel):
    no_wait: bool = False
    no_color: bool = False
    pager: bool = False
    id_only: bool = False
    resp_format: Format = Format.json
    debug: bool = False
    quiet: bool = False
    ssl_verify: bool = True
    base_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "http://localhost:8000/api/v4")
    hide_restricted_commands: bool = True
    signing_service: Optional[RepoSigningService] = RepoSigningService.esrp

    msal_client_id: NonEmptyStr
    msal_scope: NonEmptyStr
    msal_cert: Optional[str]
    msal_cert_path: Optional[FilePath]
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

    @root_validator(pre=False, skip_on_failure=True)
    def validate_msal_cert(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["msal_cert"] and not values["msal_cert_path"]:
            raise ValueError("Either msal_cert or msal_cert_path must be defined.")
        if values["msal_cert"] and values["msal_cert_path"]:
            raise ValueError("msal_cert and msal_cert_path cannot both be set.")
        return values

    def auth_fields(self) -> Dict[str, Any]:
        return {k: v for k, v in self.dict().items() if k.startswith("msal_")}


class FileConfig(Config, metaclass=OptionalFieldsMeta):
    """
    Represents a config from the settings file.

    This differs from a Config in that required options do not need to be set as they may be passed
    in as options (e.g. --msal-client-id).
    """

    @root_validator(pre=False, skip_on_failure=True)
    def validate_msal_cert(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        # skip validating msal_cert
        return values

    pass

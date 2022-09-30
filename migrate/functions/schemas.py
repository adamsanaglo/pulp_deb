from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, MissingError, validator


class StrEnum(str, Enum):

    def __repr__(self):
        return self.value


class ActionType(StrEnum):
    add = "add"
    remove = "remove"


class SourceType(StrEnum):
    vnext = "vnext"
    vcurrent = "vcurrent"


class RepoType(StrEnum):
    yum = "yum"
    apt = "apt"


class Package(BaseModel):
    name: str
    version: str
    arch: str


class DebPackage(Package):
    ...


class RpmPackage(Package):
    epoch: Optional[str]
    release: str


class Action(BaseModel):
    action_type: ActionType
    source: SourceType
    repo_name: str
    repo_type: RepoType
    release: Optional[str]
    package: Union[RpmPackage, DebPackage, None]

    @validator("package")
    def validate_package(cls, value, values):
        if not (values["source"] == "vcurrent" and values["action_type"] == "add"):
            if not value:
                raise MissingError()
        return value

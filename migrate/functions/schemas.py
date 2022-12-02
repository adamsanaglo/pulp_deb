from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel


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
    packages: Union[List[RpmPackage], List[DebPackage]]

    def translate_repo_name(self):
        if self.source == SourceType.vnext:
            if self.repo_type == RepoType.apt and self.repo_name.endswith("-apt"):
                self.repo_name = self.repo_name[:-4]
            if self.repo_type == RepoType.yum and self.repo_name.endswith("-yum"):
                self.repo_name = self.repo_name[:-4]
        elif self.source == SourceType.vcurrent:
            if self.repo_type == RepoType.apt:
                self.repo_name = f"{self.repo_name}-apt"
            if self.repo_type == RepoType.yum:
                self.repo_name = f"{self.repo_name}-yum"
        else:
            raise ValueError(f"Missing/invalid source: {self.source}")

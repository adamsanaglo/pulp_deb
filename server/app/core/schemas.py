import re
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Match, Optional, Pattern, Type, TypeVar

from pydantic import BaseModel, root_validator

uuid_regex = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")

T = TypeVar("T", bound="Identifier")


class DistroType(str, Enum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class RepoType(str, Enum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class PackageType(str, Enum):
    """Type for a package."""

    deb = "deb"
    rpm = "rpm"


class Identifier(str):
    """Represents an id in PMC."""

    pattern: Pattern[str] = re.compile(rf"^([a-z-]+)-({uuid_regex.pattern})$")
    examples: List[str]

    @classmethod
    def __get_validators__(cls: Type[T]) -> Generator[Callable[[str], T], None, None]:
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(
            pattern=cls.pattern.pattern,
            examples=cls.examples,
        )

    @classmethod
    def validate(cls: Type[T], val: str) -> T:
        """Validate an id and return a new Identifier instance."""
        if not isinstance(val, str):
            raise TypeError("string required")
        match = cls.pattern.fullmatch(val)
        if not match:
            raise ValueError("invalid id")
        return cls(val)

    @property
    def _pieces(self) -> Match[str]:
        """Break self into a match group"""
        match = self.pattern.fullmatch(str(self))
        if not match:
            raise ValueError("invalid id")
        return match

    @property
    def uuid(self) -> str:
        """Extract a uuid part from the id."""
        return self._pieces.groups()[-1]


class RepoId(Identifier):
    pattern = re.compile(rf"^repositories-(?:deb|rpm)-(apt|rpm)-({uuid_regex.pattern})$")
    examples = [
        "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558",
        "repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4",
    ]

    @property
    def type(self) -> RepoType:
        if (t := self._pieces.group(1)) == "rpm":
            return RepoType("yum")
        else:
            return RepoType(t)


class DistroId(Identifier):
    pattern = re.compile(rf"^distributions-(?:deb|rpm)-(apt|rpm)-({uuid_regex.pattern})$")
    examples = [
        "distributions-deb-apt-5ad78d51-1eae-4d5c-bea6-c00da9339315",
        "distributions-rpm-rpm-02ce62a-6cae-4c38-b53f-eb231f6b3e64",
    ]

    @property
    def type(self) -> DistroType:
        if (t := self._pieces.group(1)) == "rpm":
            return DistroType("yum")
        else:
            return DistroType(t)


class TaskId(Identifier):
    pattern = re.compile(rf"^tasks-({uuid_regex.pattern})$")
    examples = ["tasks-7788448d-b112-47a8-a310-3ccfe088e809"]


class PackageId(Identifier):
    pattern = re.compile(rf"^content-(deb|rpm)-packages-({uuid_regex.pattern})$")
    examples = [
        "content-deb-packages-39a63a9e-2081-4dfe-80eb-2c27af4b6024",
        "content-rpm-packages-21b4d540-76ef-420c-af0a-78c92b67eca0",
    ]

    @property
    def type(self) -> PackageType:
        return PackageType(self._pieces.group(1))


class Distribution(BaseModel):
    name: str
    type: DistroType
    base_path: str
    repository: Optional[RepoId]


class DistributionUpdate(BaseModel):
    name: Optional[str]
    base_path: Optional[str]
    repository: Optional[RepoId]


class Repository(BaseModel):
    name: str
    type: RepoType


class RepositoryUpdate(BaseModel):
    name: Optional[str]


class RepositoryPackageUpdate(BaseModel):
    add_packages: Optional[List[PackageId]]
    remove_packages: Optional[List[PackageId]]

    @root_validator
    @classmethod
    def validate_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["add_packages"] and not values["remove_packages"]:
            raise ValueError("Fields add_packages and remove_packages cannot both be empty.")
        return values

import re
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Match,
    Optional,
    Pattern,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, EmailStr, StrictStr, root_validator, validator

from app.core.models import Role

uuid_regex = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")

T = TypeVar("T", bound="Identifier")


class EmptyStr(StrictStr):
    max_length = 0


class NonEmptyStr(StrictStr):
    min_length = 1


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
    def validate(cls: Type[T], val: Union[str, UUID]) -> T:
        """Validate an id and return a new Identifier instance."""
        if isinstance(val, str):
            match = cls.pattern.fullmatch(val)
            if not match:
                raise ValueError("invalid id")
            return cls(val)
        elif isinstance(val, UUID):
            return cls.build_from_uuid(val)
        else:
            raise TypeError("string required")

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

    @classmethod
    def build_from_uuid(cls: Type[T], uuid: UUID) -> T:
        raise NotImplementedError


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


class Pagination(BaseModel):
    limit: int = 100
    offset: int = 0


class ListResponse(BaseModel):
    count: int
    limit: int
    offset: int


class DistributionCreate(BaseModel):
    name: NonEmptyStr
    type: DistroType
    base_path: NonEmptyStr
    repository: Optional[RepoId]


class DistributionUpdate(BaseModel):
    name: Optional[str]
    base_path: Optional[str]
    repository: Optional[RepoId]


class DistributionResponse(BaseModel):
    id: DistroId
    pulp_created: datetime
    name: str
    base_path: str
    base_url: str
    repository: Optional[RepoId]
    publication: Optional[str]


class DistributionListResponse(ListResponse):
    results: List[DistributionResponse]


class RepositoryCreate(BaseModel):
    name: NonEmptyStr
    type: RepoType


class RepositoryUpdate(BaseModel):
    name: Optional[str]


class RepositoryResponse(BaseModel):
    id: RepoId
    pulp_created: datetime
    name: str
    description: Optional[str]
    retain_repo_versions: Optional[int]


class RepositoryListResponse(ListResponse):
    results: List[RepositoryResponse]


class RepositoryPackageUpdate(BaseModel):
    add_packages: Optional[List[PackageId]]
    remove_packages: Optional[List[PackageId]]

    @root_validator
    @classmethod
    def validate_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["add_packages"] and not values["remove_packages"]:
            raise ValueError("Fields add_packages and remove_packages cannot both be empty.")
        return values


class BasePackageResponse(BaseModel):
    id: PackageId
    pulp_created: datetime
    sha256: str
    sha384: str
    sha512: str


class DebPackageResponse(BasePackageResponse):
    # https://github.com/pulp/pulp_deb/blob/6ce60082/pulp_deb/app/models/content.py#L139
    package: str
    source: Optional[str]
    version: str
    architecture: str
    section: Optional[str]
    priority: Optional[str]
    origin: Optional[str]
    tag: Optional[str]
    bugs: Optional[str]
    essential: Optional[bool]
    build_essential: Optional[bool]
    installed_size: Optional[int]
    maintainer: str
    original_maintainer: Optional[str]
    description: str
    description_md5: Optional[str]
    homepage: Optional[str]
    built_using: Optional[str]
    auto_built_package: Optional[str]
    multi_arch: Optional[str]

    # Depends et al
    breaks: Optional[str]
    conflicts: Optional[str]
    depends: Optional[str]
    recommends: Optional[str]
    suggests: Optional[str]
    enhances: Optional[str]
    pre_depends: Optional[str]
    provides: Optional[str]
    replaces: Optional[str]


class DebPackageListResponse(ListResponse):
    results: List[DebPackageResponse]


class RpmPackageResponse(BasePackageResponse):
    # https://github.com/pulp/pulp_rpm/blob/4f4aa4f1/pulp_rpm/app/models/package.py#L58
    name: str
    epoch: str
    version: str
    release: str
    arch: str
    pkgId: str
    checksum_type: str
    summary: str
    description: str
    url: str

    # pulp code comments seem to imply these are lists of dicts but in testing they seem to be
    # lists of lists so just model them as list of Any
    changelogs: List[Any]
    files: List[Any]
    requires: List[Any]
    provides: List[Any]
    conflicts: List[Any]
    obsoletes: List[Any]
    suggests: List[Any]
    enhances: List[Any]
    recommends: List[Any]
    supplements: List[Any]

    location_base: str
    location_href: str

    rpm_buildhost: str
    rpm_group: str
    rpm_license: str
    rpm_packager: str
    rpm_sourcerpm: str
    rpm_vendor: str
    rpm_header_start: Optional[int]
    rpm_header_end: Optional[int]

    size_archive: Optional[int]
    size_installed: Optional[int]
    size_package: Optional[int]

    time_build: Optional[int]
    time_file: Optional[int]


class RpmPackageListResponse(ListResponse):
    results: List[RpmPackageResponse]


class PackageResponse(BaseModel):
    __root__: Union[DebPackageResponse, RpmPackageResponse]


class PackageListResponse(ListResponse):
    results: List[PackageResponse]


class TaskResponse(BaseModel):
    task: TaskId


class TaskReadResponse(BaseModel):
    id: TaskId
    pulp_created: datetime
    state: str
    name: str
    logging_cid: Union[UUID, EmptyStr]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[Dict[str, Any]]
    worker: Optional[str]
    progress_reports: Optional[List[Dict[str, Any]]]
    created_resources: List[str]
    reserved_resources_record: List[str]


class TaskListResponse(ListResponse):
    results: List[TaskReadResponse]


class AccountCreate(BaseModel):
    id: UUID  # Must be the Azure Active Directory "oid" of the user/principal.
    name: NonEmptyStr
    is_enabled: bool = True
    role: Role
    icm_service: NonEmptyStr
    icm_team: NonEmptyStr
    contact_email: NonEmptyStr

    @validator("contact_email")
    def valid_email(cls, v: str) -> str:
        """Validate email address(es)."""
        for email in v.split(";"):
            EmailStr.validate(email)
        return v


class AccountUpdate(BaseModel):
    # reuse AccountCreate but make fields optional
    __annotations__ = {
        k: Optional[v] for k, v in AccountCreate.__annotations__.items()  # pyright: ignore
    }


class AccountResponse(AccountCreate):
    id: UUID
    created_at: datetime
    last_edited: datetime


class AccountListResponse(ListResponse):
    results: List[AccountResponse]

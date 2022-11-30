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

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    FileUrl,
    NonNegativeInt,
    PositiveInt,
    StrictStr,
    root_validator,
    validator,
)

from app.core.models import Role

T = TypeVar("T", bound="Identifier")


uuid_group = r"?P<uuid>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"


def normalize_type(type: str) -> str:
    return "yum" if type == "rpm" else type


class EmptyStr(StrictStr):
    max_length = 0


class NonEmptyStr(StrictStr):
    min_length = 1


class DistroType(str, Enum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "pypi"
    file = "file"


class RemoteType(str, Enum):
    """Type for a remote."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class RepoType(str, Enum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "python"
    file = "file"


class RepoSigningService(str, Enum):
    """What Signing Service to use to sign the repo metadata."""

    legacy = "legacy"
    esrp = "esrp"


class PackageType(str, Enum):
    """Type for a package."""

    deb = "deb"
    rpm = "rpm"
    python = "python"
    file = "file"


class TaskState(str, Enum):
    """Options for task state."""

    completed = "completed"
    failed = "failed"
    running = "running"
    waiting = "waiting"
    canceled = "canceled"
    canceling = "canceling"
    skipped = "skipped"

    def __str__(self) -> str:
        """Return value as the string representation."""
        return str(self.value)


class Identifier(str):
    """
    Represents an id in PMC.

    Based on https://pydantic-docs.helpmanual.io/usage/types/#classes-with-__get_validators__
    """

    pattern: Pattern[str] = re.compile(rf"^([a-z-]+)-({uuid_group})$")
    examples: List[str] = []

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
                raise ValueError(f"invalid id: {val}")
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
            raise ValueError(f"invalid id: {self}")
        return match

    @property
    def uuid(self) -> str:
        """Extract a uuid part from the id."""
        return self._pieces.group("uuid")

    @classmethod
    def build_from_uuid(cls: Type[T], uuid: UUID) -> T:
        raise NotImplementedError


class RepoId(Identifier):
    pattern = re.compile(
        rf"^repositories-(?:deb|rpm|python|file)-(?P<type>apt|rpm|python|file)-({uuid_group})$"
    )
    examples = [
        "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558",
        "repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4",
        "repositories-python-python-9cdb587-1c31-4dbc-9002-267f10379f67",
        "repositories-file-file-5d90abfd-0a58-4ac0-9915-42e201c07155",
    ]

    @property
    def type(self) -> RepoType:
        return RepoType(normalize_type(self._pieces.group("type")))


class RepoVersionId(Identifier):
    pattern = re.compile(
        rf"^repositories-(?:deb|rpm|python|file)-(?P<type>apt|rpm|python|file)-({uuid_group})-"
        r"versions-(\d+)"
    )
    examples = [
        "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558-versions-0",
        "repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4-versions-5",
    ]

    @property
    def type(self) -> RepoType:
        return RepoType(normalize_type(self._pieces.group("type")))


class DebRepoId(RepoId):
    pattern = re.compile(rf"^repositories-deb-apt-({uuid_group})$")
    examples = ["repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558"]

    @property
    def type(self) -> RepoType:
        return RepoType.apt


class DistroId(Identifier):
    pattern = re.compile(
        rf"^distributions-(?:deb|rpm|python|file)-(?P<type>apt|rpm|pypi|file)-({uuid_group})$"
    )
    examples = [
        "distributions-deb-apt-5ad78d51-1eae-4d5c-bea6-c00da9339315",
        "distributions-rpm-rpm-02ce62a-6cae-4c38-b53f-eb231f6b3e64",
        "distributions-python-pypi-cfd8825d-1a9d-4935-a475-9d51acc714e4",
        "distributions-file-file-41c019a5-0272-467e-ac67-be2e0a45bb21",
    ]

    @property
    def type(self) -> DistroType:
        return DistroType(normalize_type(self._pieces.group("type")))


class RemoteId(Identifier):
    pattern = re.compile(rf"^remotes-(?:deb|rpm)-(?P<type>apt|rpm)-({uuid_group})$")
    examples = [
        "remotes-deb-apt-492ed45e-a9a8-41ca-a133-7b18ad571712",
        "remotes-rpm-rpm-d3e56b3a-d816-454f-b045-503ffe41c9d1",
    ]

    @property
    def type(self) -> RemoteType:
        return RemoteType(normalize_type(self._pieces.group("type")))


class TaskId(Identifier):
    pattern = re.compile(rf"^tasks-({uuid_group})$")
    examples = ["tasks-7788448d-b112-47a8-a310-3ccfe088e809"]


class ContentId(Identifier):
    pattern = re.compile(rf"^content-(deb|rpm|python|file)-[a-z_]+-({uuid_group})$")
    examples = [
        "content-deb-packages-39a63a9e-2081-4dfe-80eb-2c27af4b6024",
        "content-deb-releases-1b6e8bba-e9a0-4070-9965-f1840164714e",
        "content-deb-release_components-be0a9766-633b-4538-a1a8-9b2a686affa0",
    ]


class PackageId(ContentId):
    pattern = re.compile(
        rf"^content-(?P<type>deb|rpm|python|file)-(packages|files)-({uuid_group})$"
    )
    examples = [
        "content-deb-packages-39a63a9e-2081-4dfe-80eb-2c27af4b6024",
        "content-rpm-packages-21b4d540-76ef-420c-af0a-78c92b67eca0",
        "content-python-packages-2322cee3-3886-45df-912d-f7afffe929b6",
        "content-file-file-56050e2b-4f9a-479d-9e12-cf6142eda69b",
    ]

    @property
    def type(self) -> PackageType:
        return PackageType(self._pieces.group("type"))


class ReleaseId(ContentId):
    pattern = re.compile(rf"^content-deb-releases-({uuid_group})$")
    examples = ["content-deb-releases-7788448d-b112-47a8-a310-3ccfe088e809"]


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
    repository: Optional[str]
    publication: Optional[str]


class DistributionListResponse(ListResponse):
    results: List[DistributionResponse]


class RemoteCreate(BaseModel):
    name: NonEmptyStr
    type: RemoteType
    url: Union[AnyHttpUrl, FileUrl]
    download_concurrency: Optional[PositiveInt]
    max_retries: Optional[NonNegativeInt]
    rate_limit: Optional[NonNegativeInt]
    distributions: Optional[List[str]]
    components: Optional[List[str]]
    architectures: Optional[List[str]]


class RemoteUpdate(BaseModel):
    name: Optional[str]
    url: Union[AnyHttpUrl, FileUrl, None]
    download_concurrency: Optional[PositiveInt]
    max_retries: Optional[NonNegativeInt]
    rate_limit: Optional[NonNegativeInt]
    distributions: Optional[List[str]]
    components: Optional[List[str]]
    architectures: Optional[List[str]]


class BaseRemoteResponse(BaseModel):
    id: RemoteId
    pulp_created: datetime
    name: str
    url: Union[AnyHttpUrl, FileUrl]
    download_concurrency: Optional[PositiveInt]
    max_retries: Optional[NonNegativeInt]
    rate_limit: Optional[NonNegativeInt]


class YumRemoteResponse(BaseRemoteResponse):
    ...


class AptRemoteResponse(YumRemoteResponse):
    distributions: Union[str, List[str]]
    components: Union[str, List[str], None]
    architectures: Union[str, List[str], None]
    _split_whitespace = validator("distributions", "components", "architectures")(
        lambda x: x.split(" ") if x else x
    )


class RemoteResponse(BaseModel):
    __root__: Union[AptRemoteResponse, YumRemoteResponse]


class RemoteListResponse(ListResponse):
    # Note that this response doesn't include the apt remote fields (distributions, etc)
    results: List[BaseRemoteResponse]


class RepositoryCreate(BaseModel):
    name: NonEmptyStr
    type: RepoType
    signing_service: Optional[RepoSigningService]
    remote: Optional[RemoteId]

    @validator("signing_service")
    def validate_signing_service(
        cls, val: Optional[RepoSigningService], values: Dict[str, Any]
    ) -> Optional[RepoSigningService]:
        if values.get("type") in [RepoType.yum, RepoType.apt]:
            if not val:
                raise ValueError("Must specify signing service")
        return val


class RepositoryUpdate(BaseModel):
    name: Optional[str]
    signing_service: Optional[RepoSigningService]
    remote: Union[RemoteId, EmptyStr, None]


class RepositoryResponse(BaseModel):
    id: RepoId
    pulp_created: datetime
    name: str
    description: Optional[str]
    retain_repo_versions: Optional[int]
    remote: Optional[RemoteId]
    latest_version: RepoVersionId


class RepositoryListResponse(ListResponse):
    results: List[RepositoryResponse]


class RepositoryPackageUpdate(BaseModel):
    add_packages: Optional[List[PackageId]]
    remove_packages: Optional[List[PackageId]]
    release: Optional[str]
    component: str = "main"
    migration: bool = False  # TODO: [MIGRATE] Remove this parameter

    @root_validator
    @classmethod
    def validate_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["add_packages"] and not values["remove_packages"]:
            raise ValueError("Fields add_packages and remove_packages cannot both be empty.")
        return values


class PublishRequest(BaseModel):
    force: Optional[bool] = False


class BasePackageResponse(BaseModel):
    id: PackageId
    pulp_created: datetime
    sha256: str
    sha384: Optional[str]
    sha512: Optional[str]


class PackageQuery(BaseModel):
    repository: Optional[RepoId]
    sha256: Optional[str]


class FilePackageResponse(BasePackageResponse):
    relative_path: str


class FullFilePackageResponse(FilePackageResponse):
    pass


class FilePackageQuery(PackageQuery):
    relative_path: Optional[str]


class FilePackageListResponse(ListResponse):
    results: List[FilePackageResponse]


class DebPackageResponse(BasePackageResponse):
    # rename "package" -> "name" and "architecture" -> "arch" to provide unified interface with rpm
    package: str = Field(..., alias="name")
    version: str
    architecture: str = Field(..., alias="arch")
    relative_path: str

    class Config:
        allow_population_by_field_name = True


class FullDebPackageResponse(DebPackageResponse):
    # https://github.com/pulp/pulp_deb/blob/6ce60082/pulp_deb/app/models/content.py#L139
    source: Optional[str]
    relative_path: str
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


class DebPackageQuery(PackageQuery):
    package: Optional[str]
    version: Optional[str]
    architecture: Optional[str]
    release: Optional[ReleaseId]


class DebPackageListResponse(ListResponse):
    results: List[DebPackageResponse]


class RpmPackageResponse(BasePackageResponse):
    name: str
    epoch: str
    version: str
    release: str
    arch: str
    location_href: str


class FullRpmPackageResponse(RpmPackageResponse):
    # https://github.com/pulp/pulp_rpm/blob/4f4aa4f1/pulp_rpm/app/models/package.py#L58
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


class RpmPackageQuery(PackageQuery):
    name: Optional[str]
    epoch: Optional[str]
    version: Optional[str]
    release: Optional[str]
    arch: Optional[str]


class RpmPackageListResponse(ListResponse):
    results: List[RpmPackageResponse]


class PythonPackageResponse(BasePackageResponse):
    filename: str
    name: str
    version: str


class FullPythonPackageResponse(PythonPackageResponse):
    # https://github.com/pulp/pulp_python/blob/938dc67e/pulp_python/app/models.py#L141
    packagetype: str
    python_version: Optional[str]
    summary: Optional[str]
    keywords: Optional[str]
    homepage: Optional[str]
    download_url: Optional[str]
    author: Optional[str]
    author_email: Optional[str]
    maintainer: Optional[str]
    maintainer_email: Optional[str]
    license: Optional[str]
    requires_python: Optional[str]
    project_url: Optional[str]
    platform: Optional[str]
    supported_platform: Optional[str]


class PythonPackageQuery(PackageQuery):
    name: Optional[str]
    filename: Optional[str]


class PythonPackageListResponse(ListResponse):
    results: List[PythonPackageResponse]


class ReleaseCreate(BaseModel):
    # pulp_deb names the identifying field "distribution" but this is confusing so we call it "name"
    distribution: str = Field(..., alias="name")
    codename: Optional[str]
    suite: Optional[str]
    components: List[str] = ["main"]
    architectures: List[str] = ["amd64", "arm64", "armhf"]

    @validator("codename", "suite", always=True)
    def default_to_name(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        return v or values.get("distribution")

    class Config:
        # this allows the pulp response (which uses distribution for name) to populate the field
        allow_population_by_field_name = True


class ReleaseResponse(ReleaseCreate):
    id: ReleaseId
    origin: str
    label: str


class ReleaseListResponse(ListResponse):
    results: List[ReleaseResponse]


class TaskQuery(BaseModel):
    reserved_resources_record: Optional[List[Identifier]]
    created_resources: Optional[Identifier]
    state: Optional[TaskState]
    name: Optional[str]
    name__contains: Optional[str]


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
    oid: UUID  # Must be the Azure Active Directory "oid" of the user/principal.
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
    oid: UUID
    created_at: datetime
    last_edited: datetime


class AccountListResponse(ListResponse):
    results: List[AccountResponse]


class AccountRepoPermissionUpdate(BaseModel):
    account_names: List[str]
    repo_regex: str
    operator: bool = False


class AccountRepoPackagePermissionUpdate(BaseModel):
    account_names: List[str]
    repo_regex: str
    package_names: List[str]


class RepoAccessResponse(BaseModel):
    account_id: UUID
    repo_id: str
    operator: bool


class OwnedPackageResponse(BaseModel):
    account_id: UUID
    repo_id: str
    package_name: str

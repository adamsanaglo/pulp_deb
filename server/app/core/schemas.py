from __future__ import annotations

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
from pydantic.main import ModelMetaclass

from app.core.config import settings
from app.core.models import Role

T = TypeVar("T", bound="Identifier")


uuid_group = r"?P<uuid>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"


def normalize_type(type: str) -> str:
    return "yum" if type == "rpm" else type


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
    # pulpcore create a "core.artifacts" distribution that we don't use but we still need to define
    # its type in order to handle the core artifact distribution that shows up in list responses
    core = "core"


class RemoteType(str, Enum):
    """Type for a remote."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp


class RepoSigningService(str, Enum):
    """What Signing Service to use to sign the repo metadata."""

    legacy = "legacy"
    esrp = "esrp"


class PackageType(str, Enum):
    """
    Type for a package. In addition to the values evaluating to strings, they also have several
    useful properties.
    """

    deb = "deb"
    deb_src = "deb_src"
    rpm = "rpm"
    python = "python"
    file = "file"

    @property
    def pulp_name_field(self) -> str:
        return self.natural_key_fields[0]

    @property
    def repo_type(self) -> RepoType:
        types = {
            "deb": RepoType.apt,
            "deb_src": RepoType.apt,
            "rpm": RepoType.yum,
            "python": RepoType.python,
            "file": RepoType.file,
        }
        return types[self.value]

    @property
    def natural_key_fields(self) -> List[str]:
        fields = {
            "deb": ["package", "version", "architecture"],
            "deb_src": ["source", "version"],
            "rpm": ["name", "epoch", "version", "release", "arch"],
            "python": ["name", "filename"],
            "file": ["relative_path"],
        }
        return fields[self.value]

    @property
    def pulp_filename_field(self) -> str:
        fields = {
            "deb": "relative_path",
            "deb_src": "relative_path",
            "rpm": "location_href",
            "python": "filename",
            "file": "relative_path",
        }
        return fields[self.value]

    @property
    def resp_model(self) -> str:
        if self == PackageType.deb_src:
            return "DebSourcePackageResponse"
        return self.title() + "PackageResponse"

    def is_homogeneous(self, other: PackageType) -> bool:
        return self.repo_type == other.repo_type


class RepoType(str, Enum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "python"
    file = "file"

    @property
    def package_types(self) -> List[PackageType]:
        types = {
            "apt": [PackageType.deb, PackageType.deb_src],
            "yum": [PackageType.rpm],
            "python": [PackageType.python],
            "file": [PackageType.file],
        }
        return types[self.value]


class PublicationType(str, Enum):
    """Type for a publication."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp
    python = "pypi"
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
        return self.name


class Identifier(str):
    """
    Represents a pulp id in PMC.

    Based on https://pydantic-docs.helpmanual.io/usage/types/#classes-with-__get_validators__
    """

    pattern: Pattern[str] = re.compile(rf"^([a-z-_]+)-({uuid_group})(-versions-\d+)?$")
    examples: List[str] = []

    def __new__(cls: Type[T], my_string: str) -> Identifier:
        """
        Use our pattern matching to instantiate the most-specific type of Identifier.

        Can instantiate Identifier subclasses with the string representation of Identifiers:
            "content-deb-packages-39a63a9e-2081-4dfe-80eb-2c27af4b6024"
        or with a full or partial pulp href:
            "content/deb/packages/39a63a9e-2081-4dfe-80eb-2c27af4b6024/"
            "/pulp/api/v3/content/deb/packages/39a63a9e-2081-4dfe-80eb-2c27af4b6024/"
        """
        if isinstance(my_string, Identifier):
            # if it's already been instantiated, short-circuit all the below.
            return my_string

        my_string = my_string.removeprefix(settings.PULP_API_PATH)
        my_string = my_string.replace("/", "-")
        my_string = my_string.strip("-")
        # Follow the subclass tree to find the most-specific subclass.
        for subclass in cls.__subclasses__():
            if subclass._is_valid(my_string):
                return subclass.__new__(subclass, my_string)

        if not cls._is_valid(my_string):
            raise ValueError(f"{my_string} is not a valid {cls}")
        return super().__new__(cls, my_string)  # default to Identifier

    @property
    def pulp_href(self) -> str:
        """Translate an Identifier back into a pulp href."""
        prefix, suffix = self.split(self.uuid)
        prefix, suffix = prefix.replace("-", "/"), suffix.replace("-", "/")
        return f"{settings.PULP_API_PATH}/{prefix}{self.uuid}{suffix}/"

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
    def _is_valid(cls: Type[T], val: str) -> bool:
        """Validate an id."""
        return bool(cls.pattern.fullmatch(val))

    @classmethod
    def validate(cls: Type[T], val: str) -> T:
        """Validate an id and return a new Identifier instance."""
        if not cls._is_valid(val):
            raise ValueError(f"invalid id: {val}")
        return cls(val)

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


class RepoId(Identifier):
    pattern = re.compile(
        r"^repositories-(?P<plugin>deb|rpm|python|file)-"
        rf"(?P<type>apt|rpm|python|file)-({uuid_group})$"
    )
    examples = [
        "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558",
        "repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4",
        "repositories-python-python-9cdb58a7-1c31-4dbc-9002-267f10379f67",
        "repositories-file-file-5d90abfd-0a58-4ac0-9915-42e201c07155",
    ]

    @property
    def type(self) -> RepoType:
        return RepoType(normalize_type(self._pieces.group("type")))

    @property
    def package_types(self) -> List[PackageType]:
        plugin = self._pieces.group("plugin")
        if plugin == "deb":
            return [PackageType.deb, PackageType.deb_src]
        return [PackageType(self._pieces.group("plugin"))]

    @property
    def publication_type(self) -> PublicationType:
        if self.type == RepoType.python:
            return PublicationType.python
        else:
            return PublicationType(self.type)


class RepoVersionId(Identifier):
    pattern = re.compile(
        rf"^repositories-(?:deb|rpm|python|file)-(?P<type>apt|rpm|python|file)-({uuid_group})-"
        r"versions-(?P<number>\d+)"
    )
    examples = [
        "repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558-versions-0",
        "repositories-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4-versions-5",
    ]

    @property
    def type(self) -> RepoType:
        return RepoType(normalize_type(self._pieces.group("type")))

    @property
    def repo_id(self) -> RepoId:
        return RepoId(re.sub(r"-versions-\d+$", "", self))

    @property
    def number(self) -> int:
        return int(self._pieces.group("number"))


class PublicationId(Identifier):
    pattern = re.compile(
        rf"^publications-(?:deb|rpm|python|file)-(?P<type>apt|rpm|pypi|file)-({uuid_group})$"
    )
    examples = [
        "publications-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558",
        "publications-rpm-rpm-11712ac6-ae6d-43b0-9494-1930337425b4",
        "publications-python-pypi-9cdb587-1c31-4dbc-9002-267f10379f67",
        "publications-file-file-5d90abfd-0a58-4ac0-9915-42e201c07155",
    ]

    @property
    def type(self) -> PublicationType:
        return PublicationType(normalize_type(self._pieces.group("type")))


class DebRepoId(RepoId):
    pattern = re.compile(rf"^repositories-(?P<plugin>deb)-(?P<type>apt)-({uuid_group})$")
    examples = ["repositories-deb-apt-13104a41-ba7a-4de0-98b3-ae6f5c263558"]

    @property
    def type(self) -> RepoType:
        return RepoType.apt


class DistroId(Identifier):
    # pulpcore create a "core.artifacts" distribution that we don't use but we still need to define
    # its id type in order to handle the core artifact distro that shows up in list responses
    pattern = re.compile(
        rf"^distributions-(?:deb|rpm|python|file|core)-"
        rf"(?P<type>apt|rpm|pypi|file|artifacts)-({uuid_group})$"
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
        (
            "^content-(?P<type>deb|rpm|python|file)-"
            rf"(?P<subtype>source_packages|packages|files)-({uuid_group})$"
        )
    )
    examples = [
        "content-deb-packages-39a63a9e-2081-4dfe-80eb-2c27af4b6024",
        "content-deb-source_packages-dd434ed1-caa6-47fe-b2c6-6ab3fdf10431",
        "content-rpm-packages-21b4d540-76ef-420c-af0a-78c92b67eca0",
        "content-python-packages-2322cee3-3886-45df-912d-f7afffe929b6",
        "content-file-file-56050e2b-4f9a-479d-9e12-cf6142eda69b",
    ]

    @property
    def type(self) -> PackageType:
        if self._pieces.group("subtype") == "source_packages":
            return PackageType(self._pieces.group("type") + "_src")
        return PackageType(self._pieces.group("type"))


class ArtifactId(ContentId):
    pattern = re.compile(rf"^artifacts-({uuid_group})$")
    examples = ["artifacts-6e04bfa9-e491-445f-9ebe-f522791570e1"]


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
    sqlite_metadata: Optional[bool] = None
    retain_repo_versions: Optional[int]
    signing_service_release_overrides: Optional[Dict[str, str]]

    @validator("sqlite_metadata")
    def validate_sqlite_metadata(
        cls, val: Optional[bool], values: Dict[str, Any]
    ) -> Optional[bool]:
        if val and values.get("type") != RepoType.yum:
            raise ValueError("The sqlite_metadata option is only available for yum repos")
        return val

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
    sqlite_metadata: Optional[bool] = None
    retain_repo_versions: Optional[int]
    signing_service_release_overrides: Optional[Dict[str, str]]


class RepositoryResponse(BaseModel):
    id: RepoId
    pulp_created: datetime
    name: str
    description: Optional[str]
    retain_repo_versions: Optional[int]
    remote: Optional[RemoteId]
    latest_version: RepoVersionId
    signing_service: Optional[str]
    signing_service_release_overrides: Optional[Dict[str, str]]

    def dict(self, *args: Any, **kwargs: Any) -> Any:
        # Most keys are set, even if they're None. Except for signing_service_release_overrides,
        # which we explicitly do not set if it's empty. Don't include that field by default for
        # repos that don't care (vast majority).
        kwargs["exclude_unset"] = True
        return super().dict(*args, **kwargs)


class RpmRepositoryResponse(RepositoryResponse):
    sqlite_metadata: bool


class RepositoryListResponse(ListResponse):
    results: List[RepositoryResponse]


class RepositoryPackageUpdate(BaseModel):
    add_packages: Optional[List[PackageId]]
    remove_packages: Optional[List[PackageId]]
    release: Optional[str]
    component: str = "main"
    superuser: bool = False
    migration: bool = False  # TODO: [MIGRATE] Remove this parameter

    @root_validator(pre=False, skip_on_failure=True)
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


class ArtifactResponse(BaseModel):
    id: ArtifactId
    pulp_created: datetime
    sha256: str
    sha384: Optional[str]
    sha512: Optional[str]


class PackageQuery(BaseModel):
    repository: Optional[RepoId]
    sha256: Optional[str]
    ordering: Optional[str]

    @staticmethod
    def package_type() -> PackageType:
        """Specifies the package type for the query."""
        raise NotImplementedError


class FilePackageResponse(BasePackageResponse):
    relative_path: str


class FullFilePackageResponse(FilePackageResponse):
    pass


class StrictFilePackageQuery(PackageQuery):
    relative_path: str

    @staticmethod
    def package_type() -> PackageType:
        return PackageType.file


class FilePackageQuery(StrictFilePackageQuery, metaclass=OptionalFieldsMeta):
    pass


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


class DebSourcePackageResponse(BaseModel):
    # rename "source" -> "name" and "architecture" -> "arch" to provide unified interface with rpm
    id: PackageId
    pulp_created: datetime
    source: str = Field(..., alias="name")
    version: str
    architecture: str = Field(..., alias="arch")
    relative_path: str
    artifacts: Dict[str, str]

    class Config:
        allow_population_by_field_name = True


class FullDebSourcePackageResponse(DebSourcePackageResponse):
    format: Optional[str]  # the format of the source package
    binary: Optional[str]  # lists binary packages which a source package can produce
    maintainer: Optional[str]
    uploaders: Optional[str]  # Names and emails of co-maintainers
    homepage: Optional[str]
    vcs_browser: Optional[str]
    vcs_arch: Optional[str]
    vcs_bzr: Optional[str]
    vcs_cvs: Optional[str]
    vcs_darcs: Optional[str]
    vcs_git: Optional[str]
    vcs_hg: Optional[str]
    vcs_mtn: Optional[str]
    vcs_snv: Optional[str]
    testsuite: Optional[str]
    dgit: Optional[str]
    standards_version: Optional[str]  # most recent version of the standards the pkg complies
    build_depends: Optional[str]
    build_depends_indep: Optional[str]
    build_depends_arch: Optional[str]
    build_conflicts: Optional[str]
    build_conflicts_indep: Optional[str]
    build_conflicts_arch: Optional[str]
    package_list: Optional[str]  # all the packages that can be built from the source package


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


class StrictDebPackageQuery(PackageQuery):
    package: str
    version: str
    architecture: str

    @staticmethod
    def package_type() -> PackageType:
        return PackageType.deb


class DebPackageQuery(StrictDebPackageQuery, metaclass=OptionalFieldsMeta):
    release: Optional[ReleaseId]
    relative_path: Optional[str]


class StrictDebSourcePackageQuery(PackageQuery):
    source: str
    version: str

    @staticmethod
    def package_type() -> PackageType:
        return PackageType.deb_src


class DebSourcePackageQuery(StrictDebSourcePackageQuery, metaclass=OptionalFieldsMeta):
    architecture: Optional[str]
    relative_path: Optional[str]
    release: Optional[ReleaseId]


class DebPackageListResponse(ListResponse):
    results: List[DebPackageResponse]


class DebSourcePackageListResponse(ListResponse):
    results: List[DebSourcePackageResponse]


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


class StrictRpmPackageQuery(PackageQuery):
    name: str
    epoch: str
    version: str
    release: str
    arch: str

    @staticmethod
    def package_type() -> PackageType:
        return PackageType.rpm


class RpmPackageQuery(StrictRpmPackageQuery, metaclass=OptionalFieldsMeta):
    pass


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


class StrictPythonPackageQuery(PackageQuery):
    name: str
    filename: str

    @staticmethod
    def package_type() -> PackageType:
        return PackageType.python


class PythonPackageQuery(StrictPythonPackageQuery, metaclass=OptionalFieldsMeta):
    pass


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


class ReleaseUpdate(BaseModel):
    add_architectures: Optional[List[str]] = None


class ReleaseResponse(ReleaseCreate):
    id: ReleaseId
    description: Optional[str]
    origin: str
    label: str


class ReleaseListResponse(ListResponse):
    results: List[ReleaseResponse]


class RepositoryBulkDelete(BaseModel):
    packages: Optional[
        List[
            Union[
                StrictRpmPackageQuery,
                StrictDebPackageQuery,
                StrictDebSourcePackageQuery,
                StrictPythonPackageQuery,
                StrictFilePackageQuery,
            ]
        ]
    ]
    release: Optional[str]
    component: str = "main"
    all: bool = False
    superuser: bool = False
    migration: bool = False  # TODO: [MIGRATE] Remove this parameter

    @root_validator(pre=False, skip_on_failure=True)
    def validate_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if (not values["all"] and not values["packages"]) or (values["all"] and values["packages"]):
            raise ValueError("You must specify either 'all' or a list of package queries.")
        return values


class TaskQuery(BaseModel):
    reserved_resources: Optional[Identifier]
    created_resources: Optional[Identifier]
    state: Optional[TaskState]
    name: Optional[str]
    name__contains: Optional[str]
    ordering: Optional[str]


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


NoOpTask = TaskReadResponse(
    id="tasks-00000000-0000-0000-0000-000000000000",
    pulp_created=datetime.now(),
    state="completed",
    name="No-Op Task",
    logging_cid="",
    created_resources=[],
    reserved_resources_record=[],
)


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


class AccountUpdate(AccountCreate, metaclass=OptionalFieldsMeta):
    pass


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

import logging
from functools import partialmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import httpx
from fastapi import UploadFile
from starlette_context import context

from app.core.schemas import (
    ContentId,
    DebRepoId,
    DistroId,
    DistroType,
    Identifier,
    PackageId,
    PackageType,
    Pagination,
    PublicationId,
    PublicationType,
    ReleaseId,
    RemoteId,
    RemoteType,
    RepoId,
    RepoType,
    RepoVersionId,
    TaskId,
)
from app.services.pulp.utils import get_client, memoize, sha256, translate_response

T = TypeVar("T", bound="PulpApi")

logger = logging.getLogger(__name__)


class TaskCancelException(Exception):
    """Exception raised when a user tries to cancel a task that can't be canceled."""

    pass


class PulpApi:
    """
    Base class used for interacting with Pulp's API.

    Cannot be used to communicate with Pulp; you must subclass this, and at a minimum you must alter
    the endpoint() member function.
    """

    @staticmethod
    async def request(*args: Any, **kwargs: Any) -> httpx.Response:
        """Send a request to Pulp."""
        logger.debug(f"Pulp Request {args}: {kwargs}")

        if not context.get("httpx_client", None):
            # lazily instantiate the client once
            logger.debug("Creating Pulp httpx client")
            context["httpx_client"] = get_client()

        # translate Identifiers back into pulp_hrefs before sending the request
        for my_arg in ("data", "params", "json"):
            for key, value in kwargs.get(my_arg, {}).items():
                if isinstance(value, Identifier):
                    kwargs[my_arg][key] = value.pulp_href

        resp = await context["httpx_client"].request(*args, **kwargs)

        logger.debug(f"Pulp Response ({resp.status_code}): {resp.text}")

        resp.raise_for_status()
        return resp  # type: ignore

    # define some methods that map to request
    get = partialmethod(request, "get")
    post = partialmethod(request, "post")
    patch = partialmethod(request, "patch")
    delete = partialmethod(request, "delete")

    @classmethod
    async def list(
        cls,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        """Call the list endpoint."""
        if not pagination:
            pagination = Pagination()

        if not params:
            params = dict()
        else:
            params = params.copy()

        params["limit"] = pagination.limit
        params["offset"] = pagination.offset

        resp = await cls.get(cls.endpoint("list", **endpoint_args), params=params)
        return translate_response(resp.json(), pagination=pagination)

    @classmethod
    async def read(cls, id: Identifier) -> Any:
        """Call the read endpoint."""
        resp = await cls.get(cls.endpoint("read", id=id))
        return translate_response(resp.json())

    @classmethod
    async def create(
        cls,
        data: Dict[str, Any],
        **endpoint_args: Any,
    ) -> Any:
        """Call the create endpoint."""
        resp = await cls.post(cls.endpoint("create", **endpoint_args), json=data)
        return translate_response(resp.json())

    @classmethod
    async def update(cls, id: Identifier, data: Dict[str, Any]) -> Any:
        """Call the update endpoint."""
        resp = await cls.patch(cls.endpoint("update", id=id), json=data)
        return translate_response(resp.json())

    @classmethod
    async def destroy(cls, id: Identifier) -> Any:
        """Call the destroy endpoint."""
        resp = await cls.delete(cls.endpoint("destroy", id=id))
        if resp.status_code == 204:
            return None
        return translate_response(resp.json())

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct the pulp uri based on id and other variables."""
        raise NotImplementedError


class SigningService(PulpApi):
    @staticmethod
    @memoize
    async def list_relevant(repo_type: str) -> Dict[str, str]:
        """
        List the signing services available for this repo type. This will also strip out the type
        from the name to present a unified interface, so for example "legacy_yum" -> "legacy", and
        the caller doesn't have to know or care that there are really two different "legacy"
        signing services in the backend.
        """
        resp = (await PulpApi.get("/signing-services/")).json()
        ret = {}
        suffix = "_" + repo_type
        for service in resp["results"]:
            if service["name"].endswith(suffix):
                ret[service["name"][: -len(suffix)]] = service["pulp_href"]
        return ret

    @staticmethod
    @memoize
    async def id_to_name() -> Dict[str, str]:
        """Return dict containing id -> service name mapping."""
        resp = translate_response((await PulpApi.get("/signing-services/")).json())
        ret = {}
        for service in resp["results"]:
            ret[service["id"]] = service["name"].removesuffix("_apt").removesuffix("_yum")
        return ret


class RepositoryApi(PulpApi):
    SS = "signing_service"
    SSRO = "signing_service_release_overrides"
    MSS = "metadata_signing_service"

    @staticmethod
    async def _set_gpg_and_signing_service_fields(data: Dict[str, Any], type: str) -> None:
        signing_service = data.pop(RepositoryApi.SS, None)
        services = await SigningService.list_relevant(type)
        if signing_service and signing_service not in services:
            raise Exception(
                f"Requested signing service '{signing_service}' is not registered in pulp."
            )

        if signing_service and type == RepoType.yum:
            data[RepositoryApi.MSS] = services[signing_service]
            data["gpgcheck"] = 1
            data["repo_gpgcheck"] = 1
        elif signing_service:  # deb
            data[RepositoryApi.SS] = services[signing_service]

        service_overrides = data.pop(RepositoryApi.SSRO, {})
        if service_overrides and type == RepoType.apt:
            data[RepositoryApi.SSRO] = {}
            for release, service in service_overrides.items():
                if service == "":
                    # removing
                    data[RepositoryApi.SSRO][release] = service
                    continue

                if service not in services:
                    raise Exception(
                        f"Requested signing service '{service}' is not registered in pulp."
                    )
                data[RepositoryApi.SSRO][release] = services[service]

    @staticmethod
    async def _translate_signing_service(repo: Dict[str, Any]) -> None:
        services = await SigningService.id_to_name()

        def _translate_key(key: str) -> None:
            if key in repo:
                value = repo.pop(key)
                repo[RepositoryApi.SS] = services.get(value, value)

        _translate_key(RepositoryApi.SS)
        _translate_key(RepositoryApi.MSS)
        if RepositoryApi.SSRO in repo:
            if not repo[RepositoryApi.SSRO]:
                # For repos that don't have overrides set (vast majority) don't set the key on the
                # pydantic model.
                repo.pop(RepositoryApi.SSRO)
            else:
                # Else translate the href of the signing service into a name.
                for key, value in repo[RepositoryApi.SSRO].items():
                    repo[RepositoryApi.SSRO][key] = services.get(value, value)

    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Call the create endpoint."""
        type = data.pop("type")
        if type in [RepoType.yum, RepoType.apt]:
            await cls._set_gpg_and_signing_service_fields(data, type)
        resp = await cls.post(cls.endpoint("create", type=type), json=data)
        ret = translate_response(resp.json())
        await cls._translate_signing_service(ret)
        return ret

    @classmethod
    async def read(cls, id: Identifier) -> Any:
        """Read, translating the signing service"""
        ret = await super().read(id)
        await cls._translate_signing_service(ret)
        return ret

    @classmethod
    async def update(cls, id: RepoId, data: Dict[str, Any]) -> Any:  # type: ignore
        if cls.SS in data or cls.SSRO in data:
            await cls._set_gpg_and_signing_service_fields(data, id.type)
        return await super().update(id, data)

    @classmethod
    async def sync(cls, id: RepoId, remote: Optional[RemoteId] = None) -> Any:
        """Call the sync endpoint."""
        if remote:
            data = {"remote": remote}
        else:
            data = {}
        resp = await cls.post(cls.endpoint("sync", id=id), json=data)
        return translate_response(resp.json())

    @classmethod
    async def update_content(
        cls,
        id: RepoId,
        add_content: Optional[List[ContentId]] = None,
        remove_content: Optional[List[ContentId]] = None,
    ) -> Any:
        """Update a repo's content by calling the repo modify endpoint."""

        def _translate_ids(ids: List[ContentId]) -> List[str]:
            return [content_id.pulp_href for content_id in ids]

        data = {}
        if add_content:
            data["add_content_units"] = _translate_ids(add_content)
        if remove_content:
            data["remove_content_units"] = _translate_ids(remove_content)

        resp = await cls.post(cls.endpoint("modify", id=id), json=data)
        return translate_response(resp.json())

    @classmethod
    async def publish(cls, id: RepoId, data: Optional[Dict[str, Any]] = None) -> Any:
        """Call the publication create endpoint."""
        if not data:
            data = {}
        data["repository"] = id
        return await PublicationApi.create(data)

    @classmethod
    async def latest_version(cls, repo_id: RepoId) -> RepoVersionId:
        """Get the latest version href for a repo id."""
        repo = await cls.read(repo_id)
        return RepoVersionId(repo["latest_version"])

    @staticmethod
    def detail_uri(type: Any) -> str:
        assert isinstance(type, (str, RepoType))

        if type == RepoType.apt:
            return "/repositories/deb/apt/"
        elif type == RepoType.yum:
            return "/repositories/rpm/rpm/"
        elif type in [RepoType.python, RepoType.file]:
            return f"/repositories/{type}/{type}/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a pulp repo uri from action and id."""

        if action == "list":
            return "/repositories/"
        elif action == "create":
            return RepositoryApi.detail_uri(kwargs["type"])
        elif action in ("read", "destroy", "update"):
            assert isinstance((id := kwargs["id"]), RepoId)
            return f"{RepositoryApi.detail_uri(id.type)}{id.uuid}/"
        elif action in ["modify", "sync"]:
            assert isinstance((id := kwargs["id"]), RepoId)
            return f"{RepositoryApi.detail_uri(id.type)}{id.uuid}/{action}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class RepoVersionApi(PulpApi):
    @classmethod
    async def list(
        cls,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        if not params:
            params = {}

        if repo_id := params.pop("repository", False):
            endpoint_args["repository"] = RepoId(repo_id)

        return await super().list(pagination, params, **endpoint_args)

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a pulp repo uri from action and id."""

        def _versions_endpoint(id: Union[RepoId, RepoVersionId]) -> str:
            return f"{RepositoryApi.detail_uri(id.type)}{id.uuid}/versions/"

        if action == "list":
            if repo_id := kwargs.get("repository", False):
                # there's no repository filter on the repository versions endpoint so we have to use
                # the /repositories/<type>/<id>/versions/ endpoint instead.
                return f"{_versions_endpoint(repo_id)}"
            return "/repository_versions/"
        elif action in ["read", "destroy"]:
            assert isinstance((id := kwargs["id"]), RepoVersionId)
            return f"{_versions_endpoint(id)}{id.number}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class PublicationApi(PulpApi):
    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Call the create endpoint."""
        repo_id = RepoId(data.pop("repository"))
        type = repo_id.publication_type

        if type == PublicationType.apt:
            data["structured"] = True
        if type == PublicationType.file:
            data["manifest"] = "FILE_MANIFEST"

        data["repository"] = repo_id
        resp = await cls.post(cls.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    @staticmethod
    def detail_uri(type: Any) -> str:
        assert isinstance(type, (str, PublicationType))

        if type == PublicationType.apt:
            return "/publications/deb/apt/"
        elif type == PublicationType.yum:
            return "/publications/rpm/rpm/"
        elif type == PublicationType.python:
            return "/publications/python/pypi/"
        elif type == PublicationType.file:
            return "/publications/file/file/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a pulp repo uri from action and id."""

        if action == "list":
            return "/publications/"
        elif action == "create":
            return PublicationApi.detail_uri(kwargs["type"])
        elif action in ["destroy", "read"]:
            assert isinstance((id := kwargs["id"]), PublicationId)
            return f"{PublicationApi.detail_uri(id.type)}{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class RemoteApi(PulpApi):
    @staticmethod
    def _translate_apt_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate apt fields (eg dists) into whitespace separated strings."""
        for field in ["distributions", "components", "architectures"]:
            if val := data.get(field, None):
                data[field] = " ".join(val)
        return data

    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Override the distro create method to set repository."""
        type = data.pop("type")
        data = cls._translate_apt_fields(data)
        resp = await cls.post(cls.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    @classmethod
    async def update(cls, id: Identifier, data: Dict[str, Any]) -> Any:
        data = cls._translate_apt_fields(data)
        return await super().update(id, data)

    @staticmethod
    def _detail_uri(type: Any) -> str:
        assert isinstance(type, (str, DistroType))

        if type == RemoteType.apt:
            return "/remotes/deb/apt/"
        elif type == RemoteType.yum:
            return "/remotes/rpm/rpm/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a distro endpoint from action and id."""
        if action == "list":
            return "/remotes/"
        elif action == "create":
            return RemoteApi._detail_uri(kwargs["type"])
        elif action in ("read", "destroy", "update"):
            assert isinstance((id := kwargs["id"]), RemoteId)
            return f"{RemoteApi._detail_uri(id.type)}{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class DistributionApi(PulpApi):
    @classmethod
    async def list(
        cls,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        """Call the list endpoint."""
        if not params:
            params = {}

        if repository := params.pop("repository", None):
            params["repository"] = repository

        return await super().list(pagination, params, **endpoint_args)

    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Override the distro create method to set repository."""
        type = data.pop("type")
        resp = await cls.post(cls.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    @staticmethod
    def _detail_uri(type: Any) -> str:
        assert isinstance(type, (str, DistroType))

        if type == DistroType.apt:
            return "/distributions/deb/apt/"
        elif type == DistroType.yum:
            return "/distributions/rpm/rpm/"
        elif type == DistroType.file:
            return "/distributions/file/file/"
        elif type == DistroType.python:
            return "/distributions/python/pypi/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a distro endpoint from action and id."""
        if action == "list":
            return "/distributions/"
        elif action == "create":
            return DistributionApi._detail_uri(kwargs["type"])
        elif action in ("read", "destroy", "update"):
            assert isinstance((id := kwargs["id"]), DistroId)
            return f"{DistributionApi._detail_uri(id.type)}{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class ArtifactApi(PulpApi):
    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Call the artifact create endpoint."""
        file = data.pop("file")
        path = cls.endpoint("create")

        resp = await cls.post(path, files={"file": file.file}, data=data)
        return translate_response(resp.json())

    @classmethod
    async def find(cls, file: UploadFile) -> Optional[Any]:
        """Find an artifact, if it exists."""
        file_sha256 = sha256(file.file)
        resp = await cls.list(params={"sha256": file_sha256})
        if resp["count"] > 0:
            return translate_response(resp["results"][0])
        return None

    @classmethod
    async def find_or_create(cls, data: Dict[str, Any]) -> Any:
        """Find or create an artifact."""
        file = data.pop("file")
        artifact = await cls.find(file)
        if artifact:
            return artifact

        artifact = await cls.create(data={"file": file})
        return artifact

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["create", "list"]:
            return "/artifacts/"
        else:
            raise ValueError(f"Could not construct endpoint for '{kwargs}'.")


class PackageApi(PulpApi):
    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Call the package create endpoint."""
        logger.debug(f"Pulp Request data {data}")
        file = data.pop("file")
        file_type = data.pop("file_type")
        path = cls.endpoint("create", type=file_type)
        logger.debug(f"Pulp Request Path {path}")

        if file_type == PackageType.python or (
            file_type == PackageType.file and "relative_path" not in data
        ):
            data["relative_path"] = file.filename

        if file_type == PackageType.deb_src:
            resp = await cls.post(path, data=data)
            logger.debug(f"Response is {translate_response(resp.json())}")
            return translate_response(resp.json())

        resp = await cls.post(path, files={"file": file.file}, data=data)
        return translate_response(resp.json())

    @classmethod
    async def list(
        cls,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        """Call the list endpoint."""
        if not params:
            params = {}

        repository = params.pop("repository", None)
        if endpoint_args["type"] in [PackageType.deb, PackageType.deb_src] and (
            release := params.get("release", None)
        ):
            if not repository:
                raise ValueError("Must supply repository when filtering by release.")

            # latest repo_version is assumed, doesn't need to be looked up
            repo_href = RepoId(repository).pulp_href
            params["release"] = f"{release.pulp_href},{repo_href}"
        elif repository:
            # Translate the repo_id into the repo_version_href pulp wants, if provided.
            repo_id = RepoId(repository)
            params["repository_version"] = await RepositoryApi.latest_version(repo_id)

        return await super().list(pagination, params, **endpoint_args)

    @classmethod
    async def get_package_name(cls, package_id: PackageId) -> Any:
        """Call PackageApi.read and parse the response to return the name of the package."""
        response = await cls.read(package_id)
        return response[package_id.type.pulp_name_field]

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        uris = {
            PackageType.rpm: "/content/rpm/packages/",
            PackageType.deb: "/content/deb/packages/",
            PackageType.deb_src: "/content/deb/source_packages/",
            PackageType.python: "/content/python/packages/",
            PackageType.file: "/content/file/files/",
        }

        if action in ["list", "create"]:
            assert isinstance((type := kwargs["type"]), PackageType)
            return uris[type]
        elif action == "read":
            assert isinstance((id := kwargs["id"]), PackageId)
            return f"{uris[id.type]}{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{kwargs}'.")


class ReleaseComponentApi(PulpApi):
    """Api for apt repo release components."""

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["create", "list"]:
            return "/content/deb/release_components/"
        else:
            raise ValueError(f"Could not construct endpoint for '{kwargs}'.")


class PackageReleaseComponentApi(PulpApi):
    """Api for association between packages and release components."""

    @classmethod
    async def find(cls, package_id: PackageId, comp_id: ContentId) -> Optional[ContentId]:
        """Find a package release component, if it exists."""
        resp = await cls.list(
            params={
                cls.package_key(package_id.type): package_id,
                "release_component": comp_id,
            },
            type=package_id.type,
        )
        if resp["count"] > 0:
            return ContentId(resp["results"][0]["id"])
        return None

    @classmethod
    async def find_or_create(cls, package_id: PackageId, comp_id: ContentId) -> ContentId:
        """Find or create a package release component."""
        prc_id = await cls.find(package_id, comp_id)
        if prc_id:
            return prc_id

        prc = await cls.create(
            data={cls.package_key(package_id.type): package_id, "release_component": comp_id},
            type=package_id.type,
        )
        return ContentId(prc["id"])

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["create", "list"]:
            assert isinstance((type := kwargs["type"]), PackageType)
            if type == PackageType.deb:
                return "/content/deb/package_release_components/"
            if type == PackageType.deb_src:
                return "/content/deb/source_release_components/"

        raise ValueError(f"Could not construct endpoint for '{kwargs}'.")

    @staticmethod
    def package_key(type: PackageType) -> str:
        if type == PackageType.deb_src:
            return "source_package"
        return "package"


class ReleaseArchitectureApi(PulpApi):
    """Api for apt repo release architectures."""

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["create", "list"]:
            return "/content/deb/release_architectures/"
        else:
            raise ValueError(f"Could not construct endpoint for '{kwargs}'.")


class ReleaseApi(PulpApi):
    """Api for apt repo releases (aka dists)."""

    @staticmethod
    async def _get_components(release_id: ReleaseId) -> Any:
        resp = await ReleaseComponentApi.list(params={"release": release_id})
        return [comp["component"] for comp in resp["results"]]

    @staticmethod
    async def _get_architectures(release_id: ReleaseId) -> Any:
        resp = await ReleaseArchitectureApi.list(params={"release": release_id})
        return [arch["architecture"] for arch in resp["results"]]

    @staticmethod
    async def _translate_signing_services(release: Dict[str, Any]) -> None:
        services = await SigningService.id_to_name()

        def _translate_key(key: str) -> None:
            if key in release:
                value = release[key]
                if value in services:
                    release["signing_service"] = services[value]

        _translate_key("signing_service")

    @classmethod
    async def list(
        cls,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        """Call the list endpoint."""
        if params and "repository" in params:
            params = params.copy()
            repo_id = DebRepoId(params.pop("repository"))
            params["repository_version"] = (await RepositoryApi.latest_version(repo_id)).pulp_href
            if "package" in params:
                params["package"] = f"{params['package']},{params['repository_version']}"

        releases = await super().list(pagination, params, **endpoint_args)

        # add in components and architectures
        for release in releases["results"]:
            release_id = ReleaseId(release["id"])
            release["components"] = await cls._get_components(release_id)
            release["architectures"] = await cls._get_architectures(release_id)
            await cls._translate_signing_services(release)

        return releases

    @staticmethod
    async def _add_items(
        api_class: Type[PulpApi], field: str, release: ReleaseId, items: List[str]
    ) -> List[ContentId]:
        content = []

        for item in items:
            response = await api_class.list(params={field: item, "release": release})
            if len(results := response["results"]) > 0:
                result = results[0]
            else:
                result = await api_class.create({field: item, "release": release})
            content_id = ContentId(result["id"])
            content.append(content_id)

        return content

    @classmethod
    async def add_components(cls, release: ReleaseId, components: List[str]) -> List[ContentId]:
        """Create a set of components for a release."""
        return await cls._add_items(ReleaseComponentApi, "component", release, components)

    @classmethod
    async def add_architectures(
        cls, release: ReleaseId, architectures: List[str]
    ) -> List[ContentId]:
        """Create a set of architectures for a release."""
        return await cls._add_items(ReleaseArchitectureApi, "architecture", release, architectures)

    @classmethod
    async def create(cls, data: Dict[str, Any], **endpoint_args: Any) -> Any:
        """Find or create the release and add it to our repo."""
        components = data.pop("components")
        architectures = data.pop("architectures")

        # find if the release already exists (eg for another repo)
        repository = data.pop("repository")
        releases = await cls.list(params=data)
        if len(releases["results"]) > 0:
            release = releases["results"][0]
        else:
            # release doesn't exist, let's create it
            resp = await cls.post(cls.endpoint("create"), json=data)
            release = translate_response(resp.json())

        # create the release comps and architectures
        release_id = ReleaseId(release["id"])
        content: List[ContentId] = [release_id]
        content.extend(await cls.add_components(release_id, components))
        content.extend(await cls.add_architectures(release_id, architectures))

        # add our release with its components and architectures to our repository
        return await RepositoryApi.update_content(repository, add_content=content)

    @classmethod
    async def get_repo_release(cls, repo: RepoId, release: str) -> Any:
        """Find a release for a repo using its name."""
        resp = await cls.list(params={"repository": repo, "distribution": release})
        if resp["count"] != 1:
            raise ValueError(f"Found {resp['count']} releases for '{release}' in repo '{repo}'.")
        return resp["results"][0]

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["list", "create"]:
            return "/content/deb/releases/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class TaskApi(PulpApi):
    @classmethod
    async def cancel(cls, id: TaskId) -> Any:
        """Call the task cancel endpoint."""
        path = cls.endpoint("cancel", id=id)
        try:
            resp = await cls.patch(path, data={"state": "canceled"})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                raise TaskCancelException(id)
            else:
                raise exc
        return translate_response(resp.json())

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a task endpoint based on action and id."""
        if action == "list":
            return "/tasks/"
        elif action in ("read", "cancel"):
            assert isinstance((id := kwargs["id"]), TaskId)
            return f"/tasks/{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class OrphanApi(PulpApi):
    @classmethod
    async def cleanup(cls, protection_time: Optional[int] = None) -> Any:
        """Call the orphan cleanup endpoint."""
        data = {}
        if protection_time is not None:
            data["orphan_protection_time"] = protection_time
        resp = await cls.post("/orphans/cleanup/", data=data)
        return translate_response(resp.json())

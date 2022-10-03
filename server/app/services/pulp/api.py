import logging
from functools import partialmethod
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx

from app.core.schemas import (
    ContentId,
    DebRepoId,
    DistroId,
    DistroType,
    Identifier,
    PackageId,
    PackageType,
    Pagination,
    ReleaseId,
    RemoteId,
    RemoteType,
    RepoId,
    RepoType,
    RepoVersionId,
    TaskId,
)
from app.services.pulp.utils import get_client, id_to_pulp_href, translate_response

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

    client: httpx.AsyncClient

    async def __aenter__(self: T) -> T:
        """Sets up a client."""
        self.client = get_client()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Closes the client."""
        await self.client.aclose()

    async def request(self, *args: Any, **kwargs: Any) -> httpx.Response:
        """Send a request to Pulp."""
        logger.debug(f"Pulp Request {args}: {kwargs}")

        resp = await self.client.request(*args, **kwargs)

        logger.debug(f"Pulp Response ({resp.status_code}): {resp.json()}")

        resp.raise_for_status()
        return resp

    # define some methods that map to request
    get = partialmethod(request, "get")
    post = partialmethod(request, "post")
    patch = partialmethod(request, "patch")
    delete = partialmethod(request, "delete")

    async def list(
        self,
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

        resp = await self.get(self.endpoint("list", **endpoint_args), params=params)
        return translate_response(resp.json(), pagination=pagination)

    async def read(self, id: Identifier) -> Any:
        """Call the read endpoint."""
        resp = await self.get(self.endpoint("read", id=id))
        return translate_response(resp.json())

    async def create(self, data: Dict[str, Any]) -> Any:
        """Call the create endpoint."""
        resp = await self.post(self.endpoint("create"), json=data)
        return translate_response(resp.json())

    async def update(self, id: Identifier, data: Dict[str, Any]) -> Any:
        """Call the update endpoint."""
        resp = await self.patch(self.endpoint("update", id=id), json=data)
        return translate_response(resp.json())

    async def destroy(self, id: Identifier) -> Any:
        """Call the destroy endpoint."""
        resp = await self.delete(self.endpoint("delete", id=id))
        return translate_response(resp.json())

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct the pulp uri based on id and other variables."""
        raise NotImplementedError


class SigningService(PulpApi):
    @staticmethod
    async def list_relevant(repo_type: str) -> Dict[str, str]:
        """
        List the signing services available for this repo type. This will also strip out the type
        from the name to present a unified interface, so for example "legacy_yum" -> "legacy", and
        the caller doesn't have to know or care that there are really two different "legacy"
        signing services in the backend.
        """
        async with PulpApi() as pa:
            resp = (await pa.get("/signing-services/")).json()
        ret = {}
        suffix = "_" + repo_type
        for service in resp["results"]:
            if service["name"].endswith(suffix):
                ret[service["name"].removesuffix(suffix)] = service["pulp_href"]
        return ret


class RepositoryApi(PulpApi):
    SS = "signing_service"
    MSS = "metadata_signing_service"
    PL = "pulp_labels"

    @staticmethod
    async def _set_gpg_fields(data: Dict[str, Any], type: str) -> None:
        signing_service = data.pop(RepositoryApi.SS, None)
        services = await SigningService.list_relevant(type)
        if signing_service not in services:
            raise Exception("Requested signing service is not registered in pulp.")

        if signing_service and type == RepoType.yum:
            data[RepositoryApi.MSS] = services[signing_service]
            data["gpgcheck"] = 1
            data["repo_gpgcheck"] = 1
        elif signing_service:  # deb
            # A work-around until https://github.com/pulp/pulp_deb/issues/641 is fixed.
            data[RepositoryApi.PL] = {RepositoryApi.SS: services[signing_service]}

    async def create(self, data: Dict[str, Any]) -> Any:
        """Call the create endpoint."""
        type = data.pop("type")
        await self._set_gpg_fields(data, type)
        if remote := data.get("remote", None):
            data["remote"] = id_to_pulp_href(remote)
        resp = await self.post(self.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    async def update(self, id: RepoId, data: Dict[str, Any]) -> Any:
        if self.SS in data:
            await self._set_gpg_fields(data, id.type)
        if data.get("remote", False):
            data["remote"] = id_to_pulp_href(data.pop("remote"))
        return await super().update(id, data)

    async def sync(self, id: RepoId, remote: Optional[RemoteId] = None) -> Any:
        """Call the create endpoint."""
        if remote:
            data = {"remote": remote}
        else:
            data = {}
        resp = await self.post(self.endpoint("sync", id=id), json=data)
        return translate_response(resp.json())

    async def update_content(
        self,
        id: RepoId,
        add_content: Optional[List[ContentId]] = None,
        remove_content: Optional[List[ContentId]] = None,
    ) -> Any:
        """Update a repo's content by calling the repo modify endpoint."""

        def _translate_ids(ids: List[ContentId]) -> List[str]:
            return [id_to_pulp_href(content_id) for content_id in ids]

        data = {}
        if add_content:
            data["add_content_units"] = _translate_ids(add_content)
        if remove_content:
            data["remove_content_units"] = _translate_ids(remove_content)

        resp = await self.post(self.endpoint("modify", id=id), json=data)
        return translate_response(resp.json())

    async def publish(self, id: RepoId) -> Any:
        """Call the publication create endpoint."""
        data: Dict[str, Any] = dict(repository=id_to_pulp_href(id))
        path = self._detail_uri(id.type, "publications")

        if id.type == RepoType.apt:
            data["structured"] = True
            # pulp-deb plugin wants us to specify the metadata signer every time we call publish,
            # so we must look up the href we stored in pulp_labels and add it here.
            details = await self.read(id)
            data[RepositoryApi.SS] = details[RepositoryApi.PL][RepositoryApi.SS]

        resp = await self.post(path, json=data)
        return translate_response(resp.json())

    async def latest_version_href(self, repo_id: RepoId) -> str:
        """Get the latest version href for a repo id."""
        repo = await self.read(repo_id)
        return id_to_pulp_href(RepoVersionId(repo["latest_version"]))

    @staticmethod
    def _detail_uri(type: Any, resource: str = "repositories") -> str:
        assert isinstance(type, (str, RepoType))

        if type == RepoType.apt:
            return f"/{resource}/deb/apt/"
        elif type == RepoType.yum:
            return f"/{resource}/rpm/rpm/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a pulp repo uri from action and id."""

        if action == "list":
            return "/repositories/"
        elif action == "create":
            return RepositoryApi._detail_uri(kwargs["type"])
        elif action in ("read", "delete", "update"):
            assert isinstance((id := kwargs["id"]), RepoId)
            return f"{RepositoryApi._detail_uri(id.type)}{id.uuid}/"
        elif action in ["modify", "sync"]:
            assert isinstance((id := kwargs["id"]), RepoId)
            return f"{RepositoryApi._detail_uri(id.type)}{id.uuid}/{action}/"
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

    async def create(self, data: Dict[str, Any]) -> Any:
        """Override the distro create method to set repository."""
        type = data.pop("type")
        data = self._translate_apt_fields(data)
        resp = await self.post(self.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    async def update(self, id: Identifier, data: Dict[str, Any]) -> Any:
        data = self._translate_apt_fields(data)
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
        elif action in ("read", "delete", "update"):
            assert isinstance((id := kwargs["id"]), RemoteId)
            return f"{RemoteApi._detail_uri(id.type)}{id.uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class DistributionApi(PulpApi):
    async def create(self, data: Dict[str, Any]) -> Any:
        """Override the distro create method to set repository."""
        if "repository" in data:
            data["repository"] = id_to_pulp_href(data["repository"])
        type = data.pop("type")
        resp = await self.post(self.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    async def update(self, id: DistroId, data: Dict[str, Any]) -> Any:
        """Override the distro update method to set repository."""
        if "repository" in data:
            data["repository"] = id_to_pulp_href(data["repository"])
        return await super().update(id, data)

    @staticmethod
    def _detail_uri(type: Any) -> str:
        assert isinstance(type, (str, DistroType))

        if type == DistroType.apt:
            return "/distributions/deb/apt/"
        elif type == DistroType.yum:
            return "/distributions/rpm/rpm/"
        else:
            raise TypeError(f"Received invalid type: {type}")

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        """Construct a distro endpoint from action and id."""
        if action == "list":
            return "/distributions/"
        elif action == "create":
            return DistributionApi._detail_uri(kwargs["type"])
        elif action in ("read", "delete", "update"):
            assert isinstance((id := kwargs["id"]), DistroId)
            uuid = id.uuid
            return f"{DistributionApi._detail_uri(id.type)}{uuid}/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class PackageApi(PulpApi):
    async def repository_packages(
        self, repo_id: RepoId, pagination: Pagination, release: Optional[ReleaseId] = None
    ) -> Any:
        """Call the package list endpoint and filter by repo id."""
        if repo_id.type == "apt":
            type = PackageType.deb
        elif repo_id.type == "yum":
            type = PackageType.rpm
        else:
            raise TypeError(f"Unsupported repository type: {repo_id.type.value}")

        async with RepositoryApi() as repo_api:
            version_href = await repo_api.latest_version_href(repo_id)
            params = {"repository_version": version_href}

        if release:
            params["release"] = f"{release.uuid},{params['repository_version']}"

        return await self.list(pagination, params, type=type)

    async def create(self, data: Dict[str, Any]) -> Any:
        """Call the package create endpoint."""
        file = data.pop("file")
        extension = Path(file.filename).suffix.lstrip(".")
        type = PackageType(extension)
        path = self.endpoint("create", type=type)

        resp = await self.post(path, files={"file": file.file}, data=data)
        return translate_response(resp.json())

    async def get_package_name(self, package_id: PackageId) -> Any:
        """Call PackageApi.read and parse the response to return the name of the package."""
        response = await self.read(package_id)
        # rpms have a "name" field, debs have a "package" field.
        if "name" in response:
            return response["name"]
        return response["package"]

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        uris = {
            PackageType.rpm: "/content/rpm/packages/",
            PackageType.deb: "/content/deb/packages/",
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

    async def find(self, package_id: ContentId, comp_id: ContentId) -> Optional[ContentId]:
        """Find a package release component, if it exists."""
        resp = await self.list(
            params={"package": package_id.uuid, "release_component": comp_id.uuid}
        )
        if resp["count"] > 0:
            return ContentId(resp["results"][0]["id"])
        return None

    async def find_or_create(self, package_id: ContentId, comp_id: ContentId) -> ContentId:
        """Find or create a package release component."""
        prc_id = await self.find(package_id, comp_id)
        if prc_id:
            return prc_id

        package = id_to_pulp_href(package_id)
        comp = id_to_pulp_href(comp_id)
        prc = await self.create(data={"package": package, "release_component": comp})
        return ContentId(prc["id"])

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["create", "list"]:
            return "/content/deb/package_release_components/"
        else:
            raise ValueError(f"Could not construct endpoint for '{kwargs}'.")


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

    async def _get_components(self, release_id: ReleaseId) -> Any:
        async with ReleaseComponentApi() as api:
            resp = await api.list(params={"release": release_id.uuid})
            return [comp["component"] for comp in resp["results"]]

    async def _get_architectures(self, release_id: ReleaseId) -> Any:
        async with ReleaseArchitectureApi() as api:
            resp = await api.list(params={"release": release_id.uuid})
            return [arch["architecture"] for arch in resp["results"]]

    async def list(
        self,
        pagination: Optional[Pagination] = None,
        params: Optional[Dict[str, Any]] = None,
        **endpoint_args: Any,
    ) -> Any:
        """Call the list endpoint."""
        if params and "repository" in params:
            params = params.copy()
            repo_id = DebRepoId(params.pop("repository"))
            async with RepositoryApi() as api:
                params["repository_version"] = await api.latest_version_href(repo_id)
            if "package" in params:
                params["package"] = f"{params['package']},{params['repository_version']}"

        releases = await super().list(pagination, params, **endpoint_args)

        # add in components and architectures
        for release in releases["results"]:
            release_id = ReleaseId(release["id"])
            release["components"] = await self._get_components(release_id)
            release["architectures"] = await self._get_architectures(release_id)

        return releases

    async def _add_items(
        self, api_class: Type[PulpApi], field: str, release: ReleaseId, items: List[str]
    ) -> List[ContentId]:
        release_href = id_to_pulp_href(release)
        content = []

        for item in items:
            async with api_class() as api:
                response = await api.list(params={field: item, "release": release.uuid})
                if len(results := response["results"]) > 0:
                    result = results[0]
                else:
                    result = await api.create({field: item, "release": release_href})
                content_id = ContentId(result["id"])
                content.append(content_id)

        return content

    async def add_components(self, release: ReleaseId, components: List[str]) -> List[ContentId]:
        """Create a set of components for a release."""
        return await self._add_items(ReleaseComponentApi, "component", release, components)

    async def add_architectures(self, release: ReleaseId, components: List[str]) -> List[ContentId]:
        """Create a set of architectures for a release."""
        return await self._add_items(ReleaseArchitectureApi, "architecture", release, components)

    async def create(self, data: Dict[str, Any]) -> Any:
        """Find or create the release and add it to our repo."""
        components = data.pop("components")
        architectures = data.pop("architectures")

        # find if the release already exists (eg for another repo)
        repository = data.pop("repository")
        releases = await self.list(params=data)
        if len(releases["results"]) > 0:
            release = releases["results"][0]
        else:
            # release doesn't exist, let's create it
            resp = await self.post(self.endpoint("create"), json=data)
            release = translate_response(resp.json())

        # create the release comps and architectures
        release_id = ReleaseId(release["id"])
        content: List[ContentId] = [release_id]
        content.extend(await self.add_components(release_id, components))
        content.extend(await self.add_architectures(release_id, architectures))

        # add our release with its components and architectures to our repository
        async with RepositoryApi() as api:
            return await api.update_content(repository, add_content=content)

    @staticmethod
    def endpoint(action: str, **kwargs: Any) -> str:
        if action in ["list", "create"]:
            return "/content/deb/releases/"
        else:
            raise ValueError(f"Could not construct endpoint for '{action}' with '{kwargs}'.")


class TaskApi(PulpApi):
    async def cancel(self, id: TaskId) -> Any:
        """Call the task cancel endpoint."""
        path = self.endpoint("cancel", id=id)
        try:
            resp = await self.patch(path, data={"state": "canceled"})
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
    async def cleanup(self, protection_time: Optional[int] = None) -> Any:
        """Call the orphan cleanup endpoint."""
        data = {}
        if protection_time is not None:
            data["orphan_protection_time"] = protection_time
        resp = await self.post("/orphans/cleanup/", data=data)
        return translate_response(resp.json())

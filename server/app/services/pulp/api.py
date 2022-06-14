import logging
from functools import partialmethod
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx

from core.schemas import (
    DistroId,
    DistroType,
    Identifier,
    PackageId,
    PackageType,
    RepoId,
    RepoType,
    TaskId,
)
from services.pulp.utils import get_client, id_to_pulp_href, translate_response

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

    async def list(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """Call the list endpoint."""
        resp = await self.get(self.endpoint("list"), params=params)
        return translate_response(resp.json())

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


class RepositoryApi(PulpApi):
    async def create(self, data: Dict[str, Any]) -> Any:
        """Call the create endpoint."""
        type = data.pop("type")
        resp = await self.post(self.endpoint("create", type=type), json=data)
        return translate_response(resp.json())

    async def update_packages(
        self,
        id: RepoId,
        add_packages: Optional[List[PackageId]],
        remove_packages: Optional[List[PackageId]],
    ) -> Any:
        """Update a repo's packages by calling the repo modify endpoint."""

        def _translate_ids(ids: List[PackageId]) -> List[str]:
            return [id_to_pulp_href(pkg_id) for pkg_id in ids]

        data = {}
        if add_packages:
            data["add_content_units"] = _translate_ids(add_packages)
        if remove_packages:
            data["remove_content_units"] = _translate_ids(remove_packages)

        resp = await self.post(self.endpoint("modify", id=id), json=data)
        return translate_response(resp.json())

    async def publish(self, id: RepoId) -> Any:
        """Call the publication create endpoint."""
        data: Dict[str, Any] = dict(repository=id_to_pulp_href(id))
        path = self._detail_uri(id.type, "publications")

        if id.type == RepoType.apt:
            data["simple"] = True

        resp = await self.post(path, json=data)
        return translate_response(resp.json())

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
        elif action == "modify":
            assert isinstance((id := kwargs["id"]), RepoId)
            return f"{RepositoryApi._detail_uri(id.type)}{id.uuid}/modify/"
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
    async def list(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """Call the package list endpoints and combine results."""
        # TODO: these responses need to be combined properly
        packages = []

        yum_resp = await self.get(self.endpoint("list", type=PackageType.rpm))
        packages.append(translate_response(yum_resp.json()))

        apt_resp = await self.get(self.endpoint("list", type=PackageType.deb))
        packages.append(translate_response(apt_resp.json()))

        return packages

    async def repository_packages(self, repo_id: RepoId) -> Any:
        """Call the package list endpoint and filter by repo id."""
        if repo_id.type == "apt":
            type = PackageType.deb
        elif repo_id.type == "yum":
            type = PackageType.rpm
        else:
            raise TypeError(f"Unsupported repository type: {repo_id.type.value}")

        async with RepositoryApi() as repo_api:
            repo = await repo_api.read(repo_id)
        version_href = repo["latest_version_href"]

        resp = await self.get(
            self.endpoint("list", type=type), params={"repository_version": version_href}
        )
        return translate_response(resp.json())

    async def create(self, data: Dict[str, Any]) -> Any:
        """Call the package create endpoint."""
        file = data.pop("file")
        extension = Path(file.filename).suffix.lstrip(".")
        type = PackageType(extension)
        path = self.endpoint("create", type=type)

        resp = await self.post(path, files={"file": file.file}, data=data)
        return translate_response(resp.json())

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
    async def cleanup(self) -> Any:
        """Call the orphan cleanup endpoint."""
        resp = await self.post("/orphans/cleanup/")
        return translate_response(resp.json())

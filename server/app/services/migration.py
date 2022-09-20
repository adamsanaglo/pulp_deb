# TODO: [MIGRATE] Remove me.
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional

import httpx

from app.core.config import settings
from app.core.schemas import PackageId, RepoId
from app.services.pulp.api import PackageApi, RepositoryApi


@asynccontextmanager
async def get_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async def raise_on_4xx_5xx(response: httpx.Response) -> None:
        response.raise_for_status()

    client = httpx.AsyncClient(
        base_url=settings.AF_QUEUE_ACTION_URL, event_hooks={"response": [raise_on_4xx_5xx]}
    )
    yield client
    await client.aclose()


async def remove_vcurrent_packages(
    package_ids: List[PackageId], repo_id: RepoId, release: Optional[str] = None
) -> None:
    """Remove a set of packages from vcurrent."""
    async with RepositoryApi() as api:
        repo = await api.read(repo_id)
        repo_name = repo["name"]

    async with get_client() as client:
        for package_id in package_ids:
            data = {
                "repo_name": repo_name,
                "repo_type": repo_id.type,
                "source": "vnext",
                "action_type": "remove",
            }
            if repo_id.type.apt:
                data["release"] = release

            async with PackageApi() as api:
                package = await api.read(package_id)
                data["package"] = {
                    "name": package.get("name") or package["package"],
                    "version": package["version"],
                    "arch": package.get("arch") or package["architecture"],
                }
                if package_id.type.rpm:
                    data["package"]["release"] = package["release"]
                    data["package"]["epoch"] = package["epoch"]

            await client.post("", json=data)

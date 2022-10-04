# TODO: [MIGRATE] Remove me.
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings
from app.core.schemas import PackageId, PackageType, RepoId
from app.services.pulp.api import PackageApi, RepositoryApi

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    pass


@asynccontextmanager
async def get_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async def raise_on_4xx_5xx(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # don't raise an HTTPStatusError as the exception handler code will think it's an
            # error from pulp.
            raise MigrationError(f"Received {e.response.status_code} response: {e}.")

    # strip out any query params (e.g. 'code') and send them separately
    base = settings.AF_QUEUE_ACTION_URL.split("?")[0]
    params = parse_qs(urlparse(settings.AF_QUEUE_ACTION_URL).query)

    client = httpx.AsyncClient(
        base_url=base,
        event_hooks={"response": [raise_on_4xx_5xx]},
        params=params,
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
            logger.info(f"[MIGRATION] Removing {package_id} from {repo_name}.")

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
                if package_id.type == PackageType.rpm:
                    data["package"]["release"] = package["release"]
                    data["package"]["epoch"] = package["epoch"]

            await client.post("", json=data)
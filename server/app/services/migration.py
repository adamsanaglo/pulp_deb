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

    data = {
        "repo_name": repo_name,
        "repo_type": repo_id.type,
        "source": "vnext",
        "action_type": "remove",
        "packages": [],
    }

    if repo_id.type.apt:
        data["release"] = release

    async with get_client() as client:
        for package_id in package_ids:

            async with PackageApi() as api:
                resp = await api.read(package_id)
                package = {
                    "name": resp.get("name") or resp["package"],
                    "version": resp["version"],
                    "arch": resp.get("arch") or resp["architecture"],
                }
                if package_id.type == PackageType.rpm:
                    package["release"] = resp["release"]
                    package["epoch"] = resp["epoch"]

                data["packages"].append(package)

        logger.info(f"[MIGRATION] Removing {len(data['packages'])} from {repo_name}.")
        resp = await client.post("", json=data)
        logger.info(f"[MIGRATION] Received {resp.status_code} response: {resp}.")

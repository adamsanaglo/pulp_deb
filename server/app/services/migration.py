# TODO: [MIGRATE] Remove me.
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
from asgi_correlation_id.context import correlation_id

from app.core.config import settings
from app.core.schemas import RepoId
from app.services.pulp.api import RepositoryApi

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    pass


@asynccontextmanager
async def get_client(
    url: str = settings.AF_QUEUE_ACTION_URL,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    # strip out any query params (e.g. 'code') and send them separately
    base = url.split("?")[0]
    params = parse_qs(urlparse(url).query)

    async def raise_on_4xx_5xx(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Don't raise an HTTPStatusError as the exception handler code will think it's an
            # error from pulp.
            # Also don't naively copy in error details, which may contain auth token in url.
            raise MigrationError(f"Received {e.response.status_code} response from {base}.")

    client = httpx.AsyncClient(
        base_url=base,
        event_hooks={"response": [raise_on_4xx_5xx]},
        params=params,
    )
    yield client
    await client.aclose()


async def remove_vcurrent_packages(
    filenames: List[str], repo_id: RepoId, task_id: str, release: Optional[str] = None
) -> None:
    """Remove a set of packages from vcurrent."""
    repo = await RepositoryApi.read(repo_id)
    repo_name = repo["name"]

    data = {
        "repo_name": repo_name,
        "repo_type": repo_id.type,
        "source": "vnext",
        "action_type": "remove",
        "packages": [{"filename": x} for x in filenames],
        "task_id": task_id,
        "correlation_id": correlation_id.get(),
    }

    if repo_id.type.apt:
        data["release"] = release

    async with get_client() as client:
        logger.info(f"[MIGRATION] Removing {len(data['packages'])} from {repo_name}.")
        response = await client.post("", json=data)
        logger.info(f"[MIGRATION] Received {response.status_code} response: {response}.")


async def list_or_retry_failures(retry: Optional[bool] = False) -> Any:
    """Lists or retries a batch of 10 failures."""
    async with get_client(url=settings.AF_FAILURE_URL) as client:
        method = "GET"
        if retry:
            method = "POST"
            logger.info("Retrying failed message batch.")

        return (await client.request(method=method, url="")).json()

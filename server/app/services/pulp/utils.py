import asyncio
import hashlib
import re
from typing import Any, AsyncGenerator, Awaitable, BinaryIO, Callable, Dict, Optional

import httpx
from asgi_correlation_id.context import correlation_id

from app.core.config import settings
from app.core.schemas import Identifier, Pagination


def get_client() -> httpx.AsyncClient:
    """Initiate a new httpx for interacting with Pulp."""
    return httpx.AsyncClient(
        headers={"Correlation-ID": str(correlation_id.get())},
        base_url=f"{settings.PULP_HOST}{settings.PULP_API_PATH}",
        auth=(settings.PULP_ADMIN_USERNAME, settings.PULP_ADMIN_PASSWORD),
        timeout=settings.PULP_TIMEOUT,
    )


def pulp_href_to_id(pulp_href: str) -> str:
    """
    Convert a pulp_href to an id.

    Example:
    /pulp/api/v3/repositories/deb/apt/d770002d-2941-41ce-a8f0-3dcf9e083400/ translates to
    repositories-deb-apt-d770002d-2941-41ce-a8f0-3dcf9e083400.
    """
    # TODO: ideally this would return an id (not a string) but there are some resource href formats
    # need to be handled (e.g. repo versions)
    return pulp_href.split(settings.PULP_API_PATH)[1].replace("/", "-").strip("-")


def id_to_pulp_href(id: Identifier) -> str:
    """Convert an id back into a pulp_href."""
    uuid = id.uuid
    pieces = [piece.replace("-", "/") for piece in id.split(uuid)]
    pieces.insert(1, uuid)
    return f"{settings.PULP_API_PATH}/{''.join(pieces)}/"


def translate_response(response_json: Any, pagination: Optional[Pagination] = None) -> Any:
    assert isinstance(response_json, dict)

    if "pulp_href" in response_json:
        response_json["id"] = pulp_href_to_id(response_json.pop("pulp_href"))
    if "results" in response_json:
        for result in response_json["results"]:
            translate_response(result)
    if "created_resources" in response_json:
        response_json["created_resources"] = [
            pulp_href_to_id(href) for href in response_json["created_resources"] if href
        ]

    for field, val in response_json.copy().items():
        if isinstance(val, str) and re.match(rf"^{settings.PULP_API_PATH}/[a-z0-9_\-/]+/$", val):
            if field.endswith("_href"):
                response_json.pop(field)
                field = field.rstrip("_href")
            response_json[field] = pulp_href_to_id(val)

        if field == "artifacts" and isinstance(val, dict):
            artifacts_dict = val  # Just for readability.
            for key, href in artifacts_dict.items():
                if re.match(rf"^{settings.PULP_API_PATH}/[a-z0-9_\-/]+/$", href):
                    artifacts_dict[key] = pulp_href_to_id(href)

    # strip out next/previous pulp links
    for link in ("next", "previous"):
        response_json.pop(link, None)

    if pagination:
        response_json["limit"] = pagination.limit
        response_json["offset"] = pagination.offset

    return response_json


def sha256(file: BinaryIO) -> str:
    file_hash = hashlib.sha256()
    buffer_size = 4 * 1048
    while chunk := file.read(buffer_size):
        file_hash.update(chunk)
    return file_hash.hexdigest()


async def yield_all(
    function: Callable[..., Awaitable[Dict[str, Any]]],
    pagination: Optional[Pagination] = None,
    *args: Any,
    **kwargs: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Calls the function provided with the args provided, and then yields the results one-at-a-time,
    loading additional pages when/if necessary.

    function: must be a pulp-api-calling async function that returns the list dict with "results"
              and "count" and such.
    pagination: The pagination parameters you wish to use. If default options are acceptable then
                you may pass None.
    """
    if pagination is None:
        pagination = Pagination()

    # Provide a default order to be extra super sure that Pulp is paginating correctly.
    if "params" not in kwargs:
        kwargs["params"] = {}
    if "ordering" not in kwargs["params"]:
        kwargs["params"]["ordering"] = "pulp_created"

    while True:
        results = await function(pagination, *args, **kwargs)
        for result in results["results"]:
            yield result
        if pagination.limit + pagination.offset < results["count"]:
            pagination.offset += pagination.limit
        else:
            return


def memoize(func) -> Any:  # type: ignore
    """
    (c) 2021 Nathan Henrie, MIT License
    https://n8henrie.com/2021/11/decorator-to-memoize-sync-or-async-functions-in-python/
    """
    cache = {}  # type: ignore

    async def memoized_async_func(*args, **kwargs):  # type: ignore
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = await func(*args, **kwargs)
        cache[key] = result
        return result

    def memoized_sync_func(*args, **kwargs):  # type: ignore
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        return result

    if asyncio.iscoroutinefunction(func):
        return memoized_async_func
    return memoized_sync_func

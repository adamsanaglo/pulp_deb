from typing import Any, Optional

import httpx
from asgi_correlation_id.context import correlation_id

from core.config import settings
from core.schemas import Identifier, Pagination


def get_client() -> httpx.AsyncClient:
    """Initiate a new httpx for interacting with Pulp."""
    return httpx.AsyncClient(
        headers={"Correlation-ID": str(correlation_id.get())},
        base_url=f"{settings.PULP_HOST}{settings.PULP_API_PATH}",
        auth=(settings.PULP_USERNAME, settings.PULP_PASSWORD),
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
    prefix = id.split(f"-{id.uuid}")[0].replace("-", "/")
    return f"{settings.PULP_API_PATH}/{prefix}/{id.uuid}/"


def translate_response(response_json: Any, pagination: Optional[Pagination] = None) -> Any:
    assert isinstance(response_json, dict)

    if "pulp_href" in response_json:
        response_json["id"] = pulp_href_to_id(response_json.pop("pulp_href"))
    if "task" in response_json:
        response_json["task"] = pulp_href_to_id(response_json["task"])
    if "results" in response_json:
        for result in response_json["results"]:
            translate_response(result)
    if "created_resources" in response_json:
        response_json["created_resources"] = [
            pulp_href_to_id(href) for href in response_json["created_resources"] if href
        ]

    # strip out next/previous pulp links
    for link in ("next", "previous"):
        response_json.pop(link, None)

    if pagination:
        response_json["limit"] = pagination.limit
        response_json["offset"] = pagination.offset

    return response_json

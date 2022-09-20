import logging
import os
from pathlib import Path
from typing import Generator, Optional
from uuid import UUID, uuid4
from contextlib import contextmanager

import httpx
from schemas import DebPackage, RpmPackage

from process_action.auth import pmcauth

VNEXT_URL = os.environ["VNEXT_URL"]
MSAL_CLIENT_ID = os.environ["MSAL_CLIENT_ID"]
MSAL_SCOPE = os.environ["MSAL_SCOPE"]
MSAL_CERT_PATH = Path(os.environ["MSAL_CERT_PATH"])
MSAL_AUTHORITY = os.environ["MSAL_AUTHORITY"]
MSAL_SNIAUTH = os.getenv("MSAL_SNIAUTH", "true").lower() in ["true", "1"]


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(
            f"Error: ({e.response.status_code}) response from {e.response.url}: {e.response.content}"
        )
        raise e


@contextmanager
def _get_client(cid: Optional[UUID] = None) -> Generator[httpx.Client, None, None]:
    if not cid:
        cid = uuid4()

    logging.info(f"Using PMC API correlation ID: {cid.hex}.")

    try:
        auth = pmcauth(
            MSAL_CLIENT_ID, MSAL_SCOPE, MSAL_CERT_PATH, MSAL_AUTHORITY, MSAL_SNIAUTH
        )
        token = auth.acquire_token()
    except Exception:
        raise Exception("Failed to retrieve AAD token")

    client = httpx.Client(
        base_url=f"{VNEXT_URL}/api/v4",
        event_hooks={"response": [_raise_for_status]},
        headers={"x-correlation-id": cid.hex, "Authorization": f"Bearer {token}"},
    )

    yield client

    client.close()


def _wait_for_task(client: httpx.Client, task_response: httpx.Response) -> None:
    try:
        task_id = task_response.json()["task"]
    except Exception as e:
        raise Exception(f"Got unexpected response: {e}")

    logging.debug(f"Polling task {task_id}.")

    while True:
        response = client.get(f"/tasks/{task_id}/")
        state = response.json()["state"]
        if state == "completed":
            return
        elif state in ["skipped", "failed", "canceled"]:
            raise Exception(f"Task failed: {response.json()}")


def _get_vnext_repo(client, repo_name):
    response = client.get(f"/repositories/", params={"name": repo_name})

    resp_json = response.json()
    if resp_json["count"] != 1:
        raise Exception(f"Found {resp_json['count']} repos for '{repo_name}'.")

    return resp_json["results"][0]


def trigger_vnext_sync(repo_name):
    with _get_client() as client:
        repo = _get_vnext_repo(client, repo_name)

        logging.info(f"Triggering sync in vnext for repo '{repo_name}'.")
        response = client.post(f"/repositories/{repo['id']}/sync/")
        _wait_for_task(client, response)

        logging.info(f"Triggering publish in vnext for repo '{repo_name}'.")
        response = client.post(f"/repositories/{repo['id']}/publish/")
        _wait_for_task(client, response)

    logging.info(f"Successfully synced '{repo_name}'.")


def remove_vnext_package(action):
    logging.info(
        f"Removing package from vnext {action.repo_name} repo: {action.package}."
    )

    with _get_client() as client:
        repo = _get_vnext_repo(client, action.repo_name)

        # find the package id
        if isinstance(action.package, DebPackage):
            params = {
                "package": action.package.name,
                "version": action.package.version,
                "architecture": action.package.arch,
            }
            response = client.get(f"/deb/packages/", params=params)
        elif isinstance(action.package, RpmPackage):
            params = action.package.dict()
            if params["epoch"] == None:
                # pulp_rpm defaults epoch to 0
                params["epoch"] = 0
            response = client.get(f"/rpm/packages/", params=params)
        else:
            raise Exception(f"Unexpected package type: {type(action.package)}")

        resp_json = response.json()
        if resp_json["count"] != 1:
            raise Exception(f"Found {resp_json['count']} packages for {action.package}.")
        package_id = resp_json["results"][0]["id"]

        # remove the package id from the repo
        data = {"remove_packages": [package_id], "migration": True}
        if isinstance(action.package, DebPackage):
            data["release"] = action.release
        response = client.patch(f"/repositories/{repo['id']}/packages/", json=data)
        _wait_for_task(client, response)

        logging.info(f"Triggering publish in vnext for repo '{repo['name']}'.")
        response = client.post(f"/repositories/{repo['id']}/publish/")
        _wait_for_task(client, response)

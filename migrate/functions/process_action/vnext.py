import logging
import os
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import Generator, Optional
from uuid import UUID, uuid4

import httpx

from process_action.auth import pmcauth
from schemas import DebPackage, RpmPackage

VNEXT_URL = os.environ["VNEXT_URL"]
MSAL_CLIENT_ID = os.environ["MSAL_CLIENT_ID"]
MSAL_SCOPE = os.environ["MSAL_SCOPE"]
MSAL_AUTHORITY = os.environ["MSAL_AUTHORITY"]
MSAL_SNIAUTH = os.getenv("MSAL_SNIAUTH", "true").lower() in ["true", "1"]

if os.getenv("MSAL_CERT_PATH"):
    MSAL_CERT = Path(os.environ["MSAL_CERT_PATH"]).expanduser().read_text()
else:
    MSAL_CERT = os.environ["MSAL_CERT"]


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if not ("publish" in e.response.url.path and e.response.status_code == 422):
            logging.error(
                f"Error: ({e.response.status_code}) response from {e.response.url}: "
                f"{e.response.content}"
            )
        raise e


def _set_auth_header(request: httpx.Request) -> None:
    try:
        auth = pmcauth(
            msal_client_id=MSAL_CLIENT_ID,
            msal_scope=MSAL_SCOPE,
            msal_authority=MSAL_AUTHORITY,
            msal_SNIAuth=MSAL_SNIAUTH,
            msal_cert=MSAL_CERT,
        )
        token = auth.acquire_token()
    except Exception as e:
        raise Exception(f"Failed to retrieve AAD token: {e}")
    request.headers["Authorization"] = f"Bearer {token}"


@contextmanager
def _get_client(cid: Optional[UUID] = None) -> Generator[httpx.Client, None, None]:
    if not cid:
        cid = uuid4()

    logging.info(f"Using PMC API correlation ID: {cid.hex}.")

    client = httpx.Client(
        base_url=f"{VNEXT_URL}/api/v4",
        event_hooks={"request": [_set_auth_header], "response": [_raise_for_status]},
        headers={"x-correlation-id": cid.hex},
        timeout=60,
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
        sleep(1)


def _get_vnext_repo(client, repo_name):
    response = client.get("/repositories/", params={"name": repo_name})

    resp_json = response.json()
    if resp_json["count"] != 1:
        raise Exception(f"Found {resp_json['count']} repos for '{repo_name}'.")

    return resp_json["results"][0]


def _publish_vnext_repo(client, repo):
    logging.info(f"Triggering publish in vnext for repo '{repo['name']}'.")

    try:
        return client.post(f"/repositories/{repo['id']}/publish/")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            logging.info("Repo contents unchanged. Skipped publish.")
        else:
            raise


def trigger_vnext_sync(repo_name):
    with _get_client() as client:
        repo = _get_vnext_repo(client, repo_name)

        logging.info(f"Triggering sync in vnext for repo '{repo_name}'.")
        response = client.post(f"/repositories/{repo['id']}/sync/")
        _wait_for_task(client, response)

        try:
            response = _publish_vnext_repo(client, repo)
            if response:
                response.json()["task"]
        except Exception as e:
            raise Exception(f"Got unexpected response: {e}")

    logging.info(f"Successfully synced '{repo_name}'.")


def remove_vnext_package(action):
    logging.info(f"Removing package from vnext {action.repo_name} repo: {action.package}.")

    with _get_client() as client:
        repo = _get_vnext_repo(client, action.repo_name)

        # find the package id
        if isinstance(action.package, DebPackage):
            params = {
                "package": action.package.name,
                "version": action.package.version,
                "architecture": action.package.arch,
            }
            response = client.get("/deb/packages/", params=params)
        elif isinstance(action.package, RpmPackage):
            params = action.package.dict()
            if params["epoch"] is None:
                # pulp_rpm defaults epoch to 0
                params["epoch"] = 0
            response = client.get("/rpm/packages/", params=params)
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

        response = _publish_vnext_repo(client, repo)
        if response:
            _wait_for_task(client, response)

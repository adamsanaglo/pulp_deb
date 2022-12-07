import logging
import os
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import Generator, Optional, Union
from uuid import UUID, uuid4

import httpx
from process_action.auth import pmcauth
from schemas import DebPackage, RepoType, RpmPackage

VNEXT_URL = os.environ["VNEXT_URL"]
MSAL_CLIENT_ID = os.environ["MSAL_CLIENT_ID"]
MSAL_SCOPE = os.environ["MSAL_SCOPE"]
MSAL_AUTHORITY = os.environ["MSAL_AUTHORITY"]
MSAL_SNIAUTH = os.getenv("MSAL_SNIAUTH", "true").lower() in ["true", "1"]

if os.getenv("MSAL_CERT_PATH"):
    MSAL_CERT = Path(os.environ["MSAL_CERT_PATH"]).expanduser().read_text()
else:
    MSAL_CERT = os.environ["MSAL_CERT"]


class RetryClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        self.retries = 1
        self.retry_status_codes = [401]

        if "retries" in kwargs:
            self.retries = kwargs.pop("retries")
        if "retry_status_codes" in kwargs:
            self.retry_status_codes = kwargs.pop("retry_status_codes")

        super().__init__(*args, **kwargs)

    def request(self, *args, **kwargs):
        retries = self.retries
        url = f"{args[0]} {args[1]}"  # 0 = method, 1 = url

        while True:
            try:
                resp = super().request(*args, **kwargs)
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code in self.retry_status_codes and retries > 0:
                    resp = e.response
                    logging.warning(f"Received {resp.status_code} response for {url}. Retrying.")
                    retries -= 1
                    continue
                else:
                    raise
            except httpx.HTTPError as e:
                # HTTPError includes various potential network problems like ConnectError
                if retries > 0:
                    logging.warning(f"HTTPError: {e} for {url}. Retrying.")
                    retries -= 1
                    continue
                else:
                    raise


def unique(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if not ("publish" in e.response.url.path and e.response.status_code == 422):
            logging.warning(
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
def get_client(cid: Optional[UUID] = None) -> Generator[httpx.Client, None, None]:
    if not cid:
        cid = uuid4()

    logging.info(f"Using PMC API correlation ID: {cid.hex}.")

    client = RetryClient(
        base_url=f"{VNEXT_URL}/api/v4",
        event_hooks={"request": [_set_auth_header], "response": [_raise_for_status]},
        headers={"x-correlation-id": cid.hex},
        timeout=60,
    )

    yield client

    client.close()


def wait_for_task(client: httpx.Client, task: Union[httpx.Response, str]) -> None:
    if isinstance(task, httpx.Response):
        try:
            task_id = task.json()["task"]
        except Exception as e:
            raise Exception(f"Got unexpected response: {e}")
    else:
        task_id = task

    logging.info(f"Polling task {task_id}.")

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
        response = client.post(f"/repositories/{repo['id']}/publish/")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            logging.info("Repo contents unchanged. Skipped publish.")
            return
        else:
            raise

    try:
        # validate that there's a task key in the response json
        _ = response.json()["task"]
    except Exception as e:
        raise Exception(f"Got unexpected response: {e}")


def _get_package_id(client, package, repo):
    """Find the package id for a given package."""
    if isinstance(package, DebPackage):
        params = {
            "package": package.name,
            "version": package.version,
            "architecture": package.arch,
            "repository": repo["id"],
        }
        response = client.get("/deb/packages/", params=params)
    elif isinstance(package, RpmPackage):
        params = package.dict()
        params["repository"] = repo["id"]
        if params["epoch"] is None:
            # pulp_rpm defaults epoch to 0
            params["epoch"] = 0
        response = client.get("/rpm/packages/", params=params)
    else:
        raise Exception(f"Unexpected package type: {type(package)}")

    resp_json = response.json()

    if resp_json["count"] == 0:
        logging.warning(f"Found 0 packages in {repo['name']} for {package}.")
        return None

    if resp_json["count"] > 1:
        raise Exception(f"Found {resp_json['count']} packages in {repo['name']} for {package}.")

    return resp_json["results"][0]["id"]


def trigger_vnext_sync(repo_name):
    with get_client() as client:
        repo = _get_vnext_repo(client, repo_name)

        logging.info(f"Triggering sync in vnext for repo '{repo_name}'.")
        response = client.post(f"/repositories/{repo['id']}/sync/")
        wait_for_task(client, response)
        _publish_vnext_repo(client, repo)


def remove_vnext_packages(action):
    errors = []
    package_ids = []

    with get_client() as client:
        repo = _get_vnext_repo(client, action.repo_name)

        # find the package ids
        for package in unique(action.packages):
            try:
                package_id = _get_package_id(client, package, repo)
                if package_id:
                    package_ids.append(package_id)
            except Exception as e:
                logging.exception(e)
                errors.append(str(e))

        if package_ids:
            # remove the package ids from the repo
            data = {"remove_packages": unique(package_ids), "migration": True}
            if action.repo_type == RepoType.apt:
                data["release"] = action.release
            response = client.patch(f"/repositories/{repo['id']}/packages/", json=data)
            wait_for_task(client, response)

            _publish_vnext_repo(client, repo)

        if errors:
            raise Exception(errors)
        else:
            logging.info(f"Removed {len(package_ids)} package(s) from {repo['name']}.")

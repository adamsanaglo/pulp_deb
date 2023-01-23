import logging
import os

from process_action.repolib import repolib
from schemas import Filename

VCURRENT_SERVER = os.environ["VCURRENT_SERVER"]
VCURRENT_PORT = os.environ["VCURRENT_PORT"]
AAD_CLIENT_ID = os.environ["AAD_CLIENT_ID"]
AAD_CLIENT_SECRET = os.environ["AAD_CLIENT_SECRET"]
AAD_RESOURCE = os.environ["AAD_RESOURCE"]
AAD_TENANT = os.environ["AAD_TENANT"]
AAD_AUTHORITY_URL = os.environ["AAD_AUTHORITY_URL"]
DISABLE_SSL_VERIFY = os.getenv("DISABLE_SSL_VERIFY", False)

api = repolib(
    VCURRENT_SERVER,
    VCURRENT_PORT,
    AAD_CLIENT_ID,
    AAD_RESOURCE,
    AAD_TENANT,
    AAD_AUTHORITY_URL,
    AAD_CLIENT_SECRET,
    version="v3",
)

if DISABLE_SSL_VERIFY:
    api.disable_ssl_verification()


def _get_repo(name):
    resp = api.list_repositories(name)
    repos = resp.json()

    if len(repos) == 0:
        return None

    if len(repos) > 1:
        raise Exception(f"Found {len(repos)} repos matching '{name}'.")

    return repos[0]


def remove_vcurrent_packages(action):
    logging.info(f"Removing package from vcurent {action.repo_name} repo: {action.packages}.")

    if not (repo := _get_repo(action.repo_name)):
        logging.warn(f"Skipping removal action. Repo '{action.repo_name}' not found.")
        return

    if not action.packages or not isinstance(action.packages[0], Filename):
        logging.warn("Skipping removal action. Empty or non-filename package list received.")
        return

    names = [x.filename for x in action.packages]
    response = api.delete_packages_by_name_and_repo_id(names, repo["id"])
    if response.status_code == 204:
        logging.info(f"Removed packages from repo {action.repo_name}.")
    elif response.status_code == 404:
        # we don't push package uploaded in vnext back to vcurrent so a 404 is possible
        logging.info("No packages found for removal from repo {action.repo_name]}.")
    else:
        logging.exception(f"Failed to delete packages: ({response.status_code}): {response.text}.")
        raise Exception("Failed to delete packages.")

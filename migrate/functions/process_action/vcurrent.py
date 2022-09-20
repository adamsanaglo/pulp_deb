import logging
import os

from schemas import RpmPackage

from process_action.repolib import repolib

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
)

if DISABLE_SSL_VERIFY:
    api.disable_ssl_verification()


def _get_repo(name):
    resp = api.list_repositories(name)
    repos = resp.json()

    if len(repos) != 1:
        raise Exception(f"Found {len(repos)} repos matching '{name}'.")

    return repos[0]


def _compare_epochs(e1, e2):
    """Returns true if epochs are equivalent."""
    return (e1 or "0") == (e2 or "0")


def _get_package(repo_id, package):
    resp = api.list_packages(
        repositoryId=repo_id,
        name=package.name,
        version=package.version,
        architecture=package.arch,
    )
    packages = resp.json()

    if isinstance(package, RpmPackage):
        # filter rpms by epoch and release
        packages = [
            pkg
            for pkg in packages
            if _compare_epochs(pkg["epoch"], package.epoch)
            and pkg["release"] == package.release
        ]

    if len(packages) != 1:
        raise Exception(
            f"Found {len(packages)} packages for {repo_id} matching {package}."
        )

    return packages[0]


def remove_vcurrent_package(action):
    logging.info(f"Removing package from vcurent {action.repo} repo: {action.package}.")
    repo = _get_repo(action.repo)
    package = _get_package(repo["id"], action.package)
    response = api.delete_package_by_id(package["id"])
    if response.status_code != 204:
        raise Exception(
            f"Failed to delete package {package['id']} ({response.status_code}): {response.text}"
        )
    logging.info(f"Deleted package {package['id']} from repo {action.repo}.")

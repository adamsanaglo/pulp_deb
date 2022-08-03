import json
import os
import random
import time
from typing import Optional, Union
from azure.storage.blob import ContentSettings, BlobServiceClient, BlobClient, BlobLeaseClient
from azure.core.exceptions import ResourceExistsError
from repoaudit.utils import RepoErrors

import logging


def _retry_acquiring_lease(
    blob_client: BlobClient,
    total_retries: int,
    interval: float
) -> BlobLeaseClient:
    """
    Try acquiring a lease on a blob 'total_retries' times with 'interval' time
    in between each retry.
    """
    x = 1
    while True:
        try:
            logging.info(f"Acquiring lease: attempt {x}")
            # acquire the lease for a short period of time so that if there is
            # a failure, the blob will quickly be available again
            return blob_client.acquire_lease(lease_duration=15, timeout=30)
        except ResourceExistsError:
            if x == total_retries:
                raise

            sleep = (interval *
                     random.uniform(0.5, 1.5))
            time.sleep(sleep)
            x += 1


def copy_dist(
    source_dist_info: dict,
    dest_repo_errors: RepoErrors,
    repo: str,
    dist: str,
    time: Optional[str] = None
) -> None:
    """Copy dist from a repository to a RepoErrors object."""
    dest_repo_errors.add(repo, dist, None)
    if "dist_errors" in source_dist_info:
        for error in source_dist_info["dist_errors"]:
            dest_repo_errors.add(repo, dist, error)

    if time:
        # change time
        dest_repo_errors.errors[repo]["dists"][dist]["time"] = time
    elif "time" in source_dist_info:
        # copy time
        dest_repo_errors.errors[repo]["dists"][dist]["time"] = source_dist_info["time"]


def write_result_to_blob(new_status: Union[dict, list], status_type: str) -> None:
    """
    Publish status result to a json blob. Fails if the json blob does not
    already exist in the storage account.
    """

    # get blob connection string and location from the function's Application Settings
    connection_string = os.getenv("pmcstatusprimary_CONNECTION")
    container_name = os.getenv("JsonContainerName")
    status_blob_name = os.getenv("JsonBlobName")

    # get clients from the connection string
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    if not container_client.exists():
        logging.error(f'Container "{container_name}" does not exist')
        return

    status_blob_client: BlobClient = blob_service_client.get_blob_client(
        container=container_name, blob=status_blob_name)

    if not status_blob_client.exists():
        logging.error(f"Blob does not exist: {container_name}, {status_blob_name}")
        return

    # acquire lease on blob
    lease = _retry_acquiring_lease(status_blob_client, total_retries=200, interval=1.0)

    # publish status to blob
    try:
        stream = status_blob_client.download_blob(lease=lease)

        current_status: dict = json.loads(stream.readall())

        mirror_filter = None
        repo_filter = None
        entry = status_type.split("-")[0]
        if status_type == "mirror-list":
            mirror_filter = set(new_status)
        elif status_type == "apt-list" or status_type == "yum-list":
            repo_filter = new_status

        if entry not in current_status or not isinstance(current_status[entry], dict):
            current_status[entry] = dict()

        if mirror_filter:
            # filter mirror urls
            current_status[entry] = {k: v for (k, v)
                                     in current_status[entry].items()
                                     if k in mirror_filter}
        elif repo_filter:
            # filter apt and yum repos/distros
            orig_errors = current_status[entry]
            filt_repo_errors = RepoErrors()
            for repo, repo_info in orig_errors.items():
                if repo in repo_filter:
                    filt_repo_errors.add(repo, None, None)
                    if "dists" in repo_info:
                        for dist, dist_info in repo_info["dists"].items():
                            if dist in repo_filter[repo]:
                                # add time to dist if its not already there
                                time = None
                                if "time" not in dist_info:
                                    time = repo_info["time"]
                                copy_dist(dist_info, filt_repo_errors, repo, dist, time=time)
                    # reset time to original
                    filt_repo_errors.errors[repo]["time"] = repo_info["time"]

            current_status[entry] = filt_repo_errors.errors

        elif status_type == "apt" or status_type == "yum":
            # update status for repositories
            # copy old status
            updated_repo_errors = RepoErrors()
            updated_repo_errors.errors.update(current_status[entry])

            for repo, repo_info in new_status.items():
                # remove repo and its dists
                old_repo_info = updated_repo_errors.errors.pop(repo, None)

                # add empty repo
                updated_repo_errors.add(repo, None, None)

                # if empty, update repository to be empty
                if repo_info["state"] != "empty" and "dists" in repo_info:

                    # add old dists in (but not ones in the update)
                    if old_repo_info and "dists" in old_repo_info:
                        for dist, old_dist_info in old_repo_info["dists"].items():
                            if dist not in repo_info["dists"]:
                                # add time to dist if its not already there
                                time = None
                                if "time" not in old_dist_info:
                                    time = old_repo_info["time"]
                                copy_dist(old_dist_info, updated_repo_errors, repo, dist, time=time)

                    # add dists from update
                    for dist, dist_info in repo_info["dists"].items():
                        time = repo_info["time"]
                        copy_dist(dist_info, updated_repo_errors, repo, dist, time=time)

                # adjust time to latest update
                updated_repo_errors.errors[repo]["time"] = repo_info["time"]

            current_status[entry] = updated_repo_errors.errors

        elif status_type == "mirror":
            current_status[entry].update(new_status)

        json_output = json.dumps(current_status, indent=4, sort_keys=True)

        status_cnt_settings = ContentSettings(
            content_type="application/json", cache_control="max-age=5, s-maxage=5")
        status_blob_client.upload_blob(
            data=json_output, content_settings=status_cnt_settings, overwrite=True, lease=lease)
    finally:
        lease.release()

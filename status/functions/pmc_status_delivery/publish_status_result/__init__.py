import json
import logging

import azure.functions as func
from .blob_helper import write_result_to_blob


def _check_mirror_status_format(status: dict) -> bool:
    """Checks if mirror status update is correctly formatted."""
    if not isinstance(status, dict):
        return False

    if len(status) == 0:
        return False

    for mirror_url, stat in status.items():

        if not isinstance(mirror_url, str):
            return False

        if not isinstance(stat, dict):
            return False

        running = stat.get("running", None)
        if not isinstance(running, bool):
            return False

        errors = stat.get("errors", None)
        if not isinstance(errors, list):
            return False

    return True


def _check_repo_status_format(status: dict) -> bool:
    """Checks if repository status update is correctly formatted."""
    if not isinstance(status, dict):
        return False

    if len(status) == 0:
        return False

    for repo, repo_data in status.items():
        if not isinstance(repo, str):
            return False

        if "state" not in repo_data:
            return False

        if repo_data["state"] != "empty":
            if "dists" not in repo_data:
                return False

            dists = repo_data["dists"]

            if not isinstance(dists, dict):
                return False

            if len(dists) == 0:
                return False

            for dist, dist_data in dists.items():
                if not isinstance(dist, str):
                    return False
                if not isinstance(dist_data, dict):
                    return False

                if "state" not in dist_data:
                    return False

                if dist_data["state"] == "error":
                    if "dist_errors" not in dist_data:
                        return False

    return True


def _check_repo_filter_format(status: dict) -> bool:
    """Checks if repository filter list is correctly formatted."""
    if not isinstance(status, dict):
        return False

    for key, val in status.items():
        if not isinstance(key, str):
            return False
        if not isinstance(val, list):
            return False

    return True


def _check_mirror_filter_format(status: list) -> bool:
    """Checks if mirror filter list is correctly formatted."""
    return isinstance(status, list)


def log_message(msg: func.QueueMessage) -> None:
    """Log message content and information."""
    logging.info(json.dumps({
        'id': msg.id,
        'body': msg.get_body().decode('utf-8'),
        'expiration_time': (msg.expiration_time.isoformat()
                            if msg.expiration_time else None),
        'insertion_time': (msg.insertion_time.isoformat()
                           if msg.insertion_time else None),
        'time_next_visible': (msg.time_next_visible.isoformat()
                              if msg.time_next_visible else None),
        'pop_receipt': msg.pop_receipt,
        'dequeue_count': msg.dequeue_count
    }))


def main(msg: func.QueueMessage) -> None:
    """
    Azure function that takes a status message and publishes the results to
    a JSON blob configured in the function's application settings.
    """
    log_message(msg)
    msg_txt = msg.get_body().decode('utf-8')

    try:
        message = json.loads(msg_txt)
    except Exception:
        logging.error("Failed to parse message as JSON")
        return

    if "status_type" not in message:
        logging.error("no status_type entry in message")
        return

    if "status" not in message:
        logging.error("no errors entry in message")
        return

    status_type = message["status_type"]
    status = message["status"]

    if status_type == "mirror":
        if not _check_mirror_status_format(status):
            logging.error("Mirror status entry is malformed")
            return
    elif status_type == "apt" or status_type == "yum":
        if not _check_repo_status_format(status):
            logging.error(f"{status_type} status entry is malformed")
            return
    elif status_type == "apt-list" or status_type == "yum-list":
        if not _check_repo_filter_format(status):
            logging.error("repo filter entry is malformed")
            return
    elif status_type == "mirror-list":
        if not _check_mirror_filter_format(status):
            logging.error("mirror filter entry is malformed")
            return
    else:
        logging.error(f"status_type {status_type} : is not apt, yum, or mirror")
        return

    write_result_to_blob(status, status_type)

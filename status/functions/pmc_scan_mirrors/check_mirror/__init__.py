import logging
import re

import azure.functions as func
from requests.exceptions import RequestException

from shared_code.utils import get_status_msg, get_url, log_message, mirror_status


def main(msg: func.QueueMessage, msgout: func.Out[str]) -> None:
    """
    Azure function that takes as input a message with a mirror url and checks
    if the mirror is running. The result is added to the results queue.
    """
    log_message(msg)

    mirror_url = msg.get_body().decode('utf-8')
    logging.info(f"Checking the mirror at {mirror_url}")

    status = mirror_status(mirror_url)

    try:
        response = get_url(mirror_url)
        links = re.findall(r"href=[\"'](.*)[\"']", response.text)

        if not links:
            status.add_error("No content on page.")

    except RequestException as e:
        status.add_error(f"Failed to connect to mirror at {mirror_url}: {e}")

    msgout.set(get_status_msg(status.to_dict(), "mirror"))

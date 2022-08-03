import datetime
import json
import logging

import azure.functions as func
from shared_code.utils import get_status_msg


def main(mytimer: func.TimerRequest,
         inputblobmirrors: str,
         msg: func.Out[func.QueueMessage],
         msgresultsqueue: func.Out[func.QueueMessage]) -> None:
    """
    Azure function that takes as input inputblobmirrors, a list of mirror
    url's, and adds them to a message queue to be checked by check_mirror.
    Also adds a filter list to the results queue to filter deleted mirrors.
    """
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.warning('The timer is past due!')

    logging.info(f'generate_apt ran at {utc_timestamp}')

    mirrors = json.loads(inputblobmirrors)

    msg.set(mirrors)
    msgresultsqueue.set(get_status_msg(mirrors, "mirror-list"))

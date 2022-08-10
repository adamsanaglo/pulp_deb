from enum import Enum
import json
import logging
import os
import azure.functions as func
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from typing import List, Tuple, Union
from functools import lru_cache
from azure.storage.queue import (
    QueueClient,
    QueueMessage,
    BinaryBase64EncodePolicy,
    BinaryBase64DecodePolicy
)


class QueueType(Enum):
    result = 1
    poison_result = 2


@lru_cache(maxsize=None)
def get_queue_client(queue_type: QueueType = QueueType.result) -> QueueClient:
    """Get queue client from function environment variables."""
    connection_string = os.getenv("pmcstatusprimary_CONNECTION")
    results_queue = os.getenv("ResultsQueueName")
    if queue_type == QueueType.poison_result:
        results_queue += "-poison"
    elif queue_type != QueueType.result:
        raise TypeError(f"unknown {queue_type=}")

    queue_client = QueueClient.from_connection_string(
        connection_string,
        results_queue,
        message_encode_policy=BinaryBase64EncodePolicy(),
        message_decode_policy=BinaryBase64DecodePolicy()
    )
    return queue_client


def move_msg_to_poison(msg: QueueMessage) -> None:
    """
    Move a message from the results queue to the poison queue. This will also delete
    the message from the results queue once it has moved to the poison queue.
    """
    poison_client = get_queue_client(queue_type=QueueType.poison_result)

    try:
        poison_client.send_message(msg.content)
    except ResourceNotFoundError:
        try:
            poison_client.create_queue()
        except ResourceExistsError:
            # in case there is a race of two function trying to create the poison queue
            pass
        poison_client.send_message(msg.content)

    delete_messages([msg])


def receive_messages(batch_size: int) -> List[QueueMessage]:
    """
    Try to receive batch_size number of messages from the results queue. If
    no messages are in the queue, then an empty list is returned.

    Receiving a message makes the message invisible in the queue for 30 seconds.
    To actually delete the message from the queue requires that it be explicitly
    deleted. Best practice is to delete the message only after the operations
    associated with that message have complete.
    """
    queue_client = get_queue_client()
    messages = queue_client.receive_messages(messages_per_page=batch_size)
    batch = next(messages.by_page(), None)
    if batch is None:
        return []

    return list(batch)


def delete_messages(messages: List[QueueMessage]) -> None:
    """Delete a list of messages from the results queue."""
    queue_client = get_queue_client()
    for msg in messages:
        queue_client.delete_message(msg)


def convert_message(msg: func.QueueMessage) -> QueueMessage:
    """Convert a functions message to a queue storage message."""
    msg_conv = QueueMessage()
    msg_conv.id = msg.id
    msg_conv.inserted_on = msg.insertion_time
    msg_conv.expires_on = msg.expiration_time
    msg_conv.dequeue_count = msg.dequeue_count
    msg_conv.content = msg.get_body()
    msg_conv.pop_receipt = msg.pop_receipt
    msg_conv.next_visible_on = msg.time_next_visible
    return msg_conv


def _check_mirror_status_format(status: dict) -> bool:
    """Checks if mirror status update is correctly formatted."""
    if not isinstance(status, dict):
        return False

    if len(status) == 0:
        return False

    for mirror_url, stat in status.items():

        if not isinstance(mirror_url, str):
            return False

        try:
            running = stat["running"]
            errors = stat["errors"]
        except (TypeError, KeyError):
            return False

        if not isinstance(errors, list):
            return False

        if not isinstance(running, bool):
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

        try:
            if repo_data["state"] != "empty":
                dists = repo_data["dists"]

                if not isinstance(dists, dict) or not len(dists):
                    return False

                for dist, dist_data in dists.items():
                    if not isinstance(dist, str):
                        return False
                    if dist_data["state"] == "error" and "dist_errors" not in dist_data:
                        return False
        except (TypeError, KeyError):
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


def get_msg_str(msg: QueueMessage) -> str:
    if isinstance(msg.content, str):
        return msg.content

    if isinstance(msg.content, (bytes, bytearray)):
        return bytes(msg.content).decode('utf-8')

    raise TypeError(
        f'response is expected to be either of '
        f'str, bytes, or bytearray, got {type(msg.content).__name__}'
    )


def log_message(msg: QueueMessage) -> None:
    """Log message content and information."""
    logging.info(json.dumps({
        'id': msg.id,
        'body': get_msg_str(msg),
        'expiration_time': (msg.expires_on.isoformat()
                            if msg.expires_on else None),
        'insertion_time': (msg.inserted_on.isoformat()
                           if msg.inserted_on else None),
        'time_next_visible': (msg.next_visible_on.isoformat()
                              if msg.next_visible_on else None),
        'pop_receipt': msg.pop_receipt,
        'dequeue_count': msg.dequeue_count
    }))


def parse_message(msg: QueueMessage) -> Tuple[str, Union[dict, list]]:
    """
    Gets the status_type and status from a message. Raises a ValueError
    if the message has format errors, or TypeError if the message content
    is not a str, bytes, or bytesarray.
    """
    log_message(msg)
    msg_txt = get_msg_str(msg)

    try:
        message = json.loads(msg_txt)
    except Exception:
        logging.error("Failed to parse message as JSON")
        raise ValueError

    if "status_type" not in message:
        logging.error("no status_type entry in message")
        raise ValueError

    if "status" not in message:
        logging.error("no errors entry in message")
        raise ValueError

    status_type = message["status_type"]
    status = message["status"]

    if status_type == "mirror":
        if not _check_mirror_status_format(status):
            logging.error("Mirror status entry is malformed")
            raise ValueError
    elif status_type == "apt" or status_type == "yum":
        if not _check_repo_status_format(status):
            logging.error(f"{status_type} status entry is malformed")
            raise ValueError
    elif status_type == "apt-list" or status_type == "yum-list":
        if not _check_repo_filter_format(status):
            logging.error("repo filter entry is malformed")
            raise ValueError
    elif status_type == "mirror-list":
        if not _check_mirror_filter_format(status):
            logging.error("mirror filter entry is malformed")
            raise ValueError
    else:
        logging.error(f"unknown {status_type=}")
        raise ValueError

    return status_type, status

import time

import azure.functions as func
from .blob_helper import flush_status, lease_status_blob, update_status
from .queue_helper import convert_message, move_msg_to_poison, parse_message, receive_messages
from azure.storage.queue import QueueMessage

QUANTUM_TIME_SEC = 30
BATCH_SIZE = 10


def apply_message(msg: QueueMessage, current_status: dict) -> None:
    """Apply a status update contained in a message."""
    try:
        status_type, status = parse_message(msg)
    except (ValueError, TypeError):
        return

    update_status(current_status, status, status_type)


def main(msg: func.QueueMessage) -> None:
    """
    Azure function that takes a batch of status message and publishes the results to
    a JSON blob configured in the function's application settings.
    """

    with lease_status_blob(lease_duration=QUANTUM_TIME_SEC+30) as (lease, current_status):
        # publish message that triggered function
        active_messages = []
        msg_conv = convert_message(msg)
        apply_message(msg_conv, current_status)
        active_messages = flush_status(current_status, lease, active_messages)

        # check for other messages in the queue to publish
        start_time = time.time()
        while True:
            quantum_elapsed = (time.time() - start_time) > QUANTUM_TIME_SEC
            if quantum_elapsed:
                return

            messages = receive_messages(BATCH_SIZE)

            if not messages:
                return
            for msg in messages:
                if msg.dequeue_count > 1:
                    active_messages = flush_status(current_status, lease, active_messages)

                if msg.dequeue_count > 5:
                    move_msg_to_poison(msg)
                else:
                    apply_message(msg, current_status)
                    active_messages.append(msg)

            active_messages = flush_status(current_status, lease, active_messages)

import json
import logging
import os

import azure.functions as func
from azure.servicebus import ServiceBusClient, ServiceBusMessage


def main(req: func.HttpRequest) -> func.HttpResponse:
    messages = []
    connectionString = os.environ["AzureServiceBusConnectionString"]
    if req.method.upper() == "POST":
        logging.info("Retrying failed messages!")
        retry = True
    else:
        logging.info("Listing failed messages.")
        retry = False

    with ServiceBusClient.from_connection_string(
        connectionString
    ) as client, client.get_queue_receiver(
        "pmcmigrate-failed",
    ) as receiver, client.get_queue_sender(
        "pmcmigrate"
    ) as sender:
        for msg in receiver.receive_messages(max_wait_time=1, max_message_count=10):
            body = next(msg.body).decode("utf-8")
            messages.append(json.loads(body))
            if retry:
                sender.send_messages([ServiceBusMessage(body=body)])
                receiver.complete_message(msg)

    logging.info(f"[MESSAGES]: {messages}")
    return func.HttpResponse(status_code=200, body=json.dumps(messages))

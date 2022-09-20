import json
import logging

import azure.functions as func
from pydantic import ValidationError
from schemas import Action


def main(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    try:
        data = req.get_json()
    except Exception as e:
        error = f"Error processing json: {e}."
        logging.error(error)
        return func.HttpResponse(error, status_code=422)

    try:
        action = Action(**req.get_json())
    except ValidationError as e:
        error = f"ValidationError: {e}."
        logging.error(error)
        return func.HttpResponse(error, status_code=422)

    msg.set(action.json())

    logging.info(f"[QUEUED]: {action}")
    return func.HttpResponse()
